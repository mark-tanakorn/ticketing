import asyncio
import imaplib
import email
import logging
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, List

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType


@register_node(
    node_type="email_listener",
    category=NodeCategory.COMMUNICATION,
    name="Email Listener",
    description=(
        "Pauses the workflow until a matching email arrives (IMAP polling). "
        "Supports saved credentials via credential_id and optimized searching to only inspect emails after activation."
    ),
    icon="fa-solid fa-envelope",
    version="1.6.0",
)
class EmailListenerNode(Node):
    logger = logging.getLogger(__name__)

    @classmethod
    def get_input_ports(cls):
        return [
            {
                "name": "trigger",
                "type": PortType.SIGNAL,
                "display_name": "Trigger",
                "description": "Optional signal input; node starts listening when executed.",
                "required": False,
            },
            {
                "name": "context",
                "type": PortType.UNIVERSAL,
                "display_name": "Context",
                "description": "Optional context passed through to outputs.",
                "required": False,
            },
        ]

    @classmethod
    def get_output_ports(cls):
        return [
            {
                "name": "email",
                "type": PortType.UNIVERSAL,
                "display_name": "Email Body",
                "description": "Cleaned body text (main message extracted from email).",
                "required": True,
            },
            {
                "name": "subject",
                "type": PortType.UNIVERSAL,
                "display_name": "Subject",
                "description": "Email subject.",
                "required": True,
            },
            {
                "name": "sender",
                "type": PortType.UNIVERSAL,
                "display_name": "Sender",
                "description": "From header (decoded).",
                "required": True,
            },
            {
                "name": "content",
                "type": PortType.UNIVERSAL,
                "display_name": "Content",
                "description": "Best-effort plain text body (falls back to HTML stripped).",
                "required": True,
            },
            {
                "name": "context",
                "type": PortType.UNIVERSAL,
                "display_name": "Context",
                "description": "Pass-through of input context.",
                "required": False,
            },
        ]

    @classmethod
    def get_config_schema(cls):
        return {
            # Credentials (preferred)
            "credential_id": {
                "type": "credential",
                "label": "Email/IMAP Credential",
                "description": "Select a saved credential (email_address/username + app_password/password).",
                "required": False,
                "default": None,
            },
            # Connection
            "provider": {
                "type": "select",
                "label": "Provider",
                "description": "Select a preset provider or use Custom IMAP.",
                "required": True,
                "default": "gmail",
                "options": [
                    {"label": "Gmail", "value": "gmail"},
                    {"label": "Outlook / Office365", "value": "outlook"},
                    {"label": "Yahoo", "value": "yahoo"},
                    {"label": "Custom IMAP", "value": "custom"},
                ],
            },
            "custom_imap_server": {
                "type": "text",
                "label": "Custom IMAP Server",
                "description": "Used when Provider = Custom IMAP (e.g., imap.example.com).",
                "required": False,
                "default": "",
            },
            "custom_imap_port": {
                "type": "number",
                "label": "Custom IMAP Port",
                "description": "Used when Provider = Custom IMAP (usually 993).",
                "required": False,
                "default": 993,
            },
            "folder": {
                "type": "text",
                "label": "Folder",
                "description": "IMAP folder to monitor (default INBOX).",
                "required": False,
                "default": "INBOX",
            },
            # Fallback auth
            "email_address": {
                "type": "text",
                "label": "Email Address (fallback)",
                "description": "Used only if no credential is selected.",
                "required": False,
                "default": "",
            },
            "password": {
                "type": "password",
                "label": "Password / App Password (fallback)",
                "description": "Used only if no credential is selected.",
                "required": False,
                "secret": True,
                "default": "",
            },
            # Polling
            "polling_interval_seconds": {
                "type": "number",
                "label": "Polling Interval (seconds)",
                "description": "How often to check for new email.",
                "required": True,
                "default": 5,
            },
            "timeout_seconds": {
                "type": "number",
                "label": "Timeout (seconds)",
                "description": "Stop waiting after this many seconds (0 = wait forever).",
                "required": True,
                "default": 0,
            },
            "search_mode": {
                "type": "select",
                "label": "IMAP Search Mode",
                "description": "Candidate selection mode. 'all' is most reliable; use SINCE optimization to avoid scanning old mail.",
                "required": True,
                "default": "all",
                "options": [
                    {"label": "ALL (recommended)", "value": "all"},
                    {"label": "UNSEEN (unread)", "value": "unseen"},
                    {"label": "RECENT", "value": "recent"},
                ],
            },
            "use_since_optimization": {
                "type": "checkbox",
                "label": "Optimize Search (SINCE today)",
                "description": "Adds IMAP SINCE <today> to avoid scanning the entire mailbox.",
                "required": True,
                "default": True,
            },
            "only_after_activation": {
                "type": "checkbox",
                "label": "Only After Activation Time",
                "description": "If enabled, will only match emails whose Date is strictly after the node activation timestamp.",
                "required": True,
                "default": True,
            },
            "max_candidates_per_poll": {
                "type": "number",
                "label": "Max Candidates per Poll",
                "description": "Limit how many newest messages to inspect each poll (0 = no limit).",
                "required": True,
                "default": 30,
            },
            "reconnect_on_error": {
                "type": "checkbox",
                "label": "Reconnect on IMAP Error",
                "description": "Reconnect and continue polling when IMAP operations fail.",
                "required": True,
                "default": True,
            },
            "noop_keepalive_every_polls": {
                "type": "number",
                "label": "NOOP Keepalive (polls)",
                "description": "Send IMAP NOOP every N polls to keep the connection alive (0 = disabled).",
                "required": True,
                "default": 10,
            },
            # Filters
            "from_filter": {
                "type": "text",
                "label": "From Filter (contains)",
                "description": "Optional: only match emails whose From contains this string (case-insensitive).",
                "required": False,
                "default": "",
            },
            "subject_contains": {
                "type": "text",
                "label": "Subject Contains",
                "description": "Optional: only match emails whose subject contains this text (case-insensitive).",
                "required": False,
                "default": "",
            },
            # Post-processing
            "mark_as_read": {
                "type": "checkbox",
                "label": "Mark as Read",
                "description": "If enabled, marks the matched email as seen (\\Seen).",
                "required": True,
                "default": False,
            },
            # Logs
            "poll_logs": {
                "type": "select",
                "label": "Poll Logs",
                "description": "Controls per-poll logging verbosity. Use Info to see polling even if your app filters DEBUG.",
                "required": True,
                "default": "info",
                "options": [
                    {"label": "Off", "value": "off"},
                    {"label": "Info", "value": "info"},
                    {"label": "Debug", "value": "debug"},
                ],
            },
            "log_candidate_headers": {
                "type": "checkbox",
                "label": "Log Candidate Headers",
                "description": "Logs basic headers for inspected candidates (From/Subject/Date/Message-ID).",
                "required": True,
                "default": False,
            },
            "log_skips_before_activation": {
                "type": "checkbox",
                "label": "Log Skips (before activation)",
                "description": "If enabled, logs when messages are skipped because they are before activation time.",
                "required": True,
                "default": False,
            },
        }

    # -------------------------
    # Small utilities
    # -------------------------

    def _poll_level(self) -> Optional[int]:
        mode = (self.config.get("poll_logs") or "info").lower().strip()
        if mode == "off":
            return None
        if mode == "debug":
            return logging.DEBUG
        return logging.INFO

    def _log(self, level: int, msg: str) -> None:
        self.logger.log(level, msg)

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        try:
            if value is None or value == "":
                return None
            return int(value)
        except Exception:
            return None

    # -------------------------
    # IMAP helpers
    # -------------------------

    def _resolve_imap_settings(self) -> Tuple[str, int]:
        provider = (self.config.get("provider") or "gmail").lower().strip()
        if provider == "gmail":
            return ("imap.gmail.com", 993)
        if provider == "outlook":
            return ("outlook.office365.com", 993)
        if provider == "yahoo":
            return ("imap.mail.yahoo.com", 993)

        host = (self.config.get("custom_imap_server") or "").strip()
        port = int(self.config.get("custom_imap_port") or 993)
        if not host:
            raise ValueError("Custom IMAP selected but custom_imap_server is empty.")
        return (host, port)

    def _resolve_folder(self) -> str:
        return (self.config.get("folder") or "INBOX").strip()

    @staticmethod
    def _quote_mailbox(mailbox: str) -> str:
        mb = (mailbox or "").strip()
        mb = mb.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{mb}"'

    def _get_auth_from_credentials(self, input_data: NodeExecutionInput) -> Tuple[str, str]:
        cred_id = self._safe_int(self.config.get("credential_id"))

        if cred_id is not None and input_data.credentials:
            cred = input_data.credentials.get(cred_id)
            if cred:
                username = (cred.get("email_address") or cred.get("username") or cred.get("email") or "").strip()
                password = cred.get("app_password") or cred.get("password") or cred.get("token") or ""
                if username and password:
                    return username, password

        username = (self.config.get("email_address") or "").strip()
        password = self.config.get("password") or ""
        if not username:
            raise ValueError("Missing email username. Provide credential_id or fill email_address (fallback).")
        if not password:
            raise ValueError("Missing email password. Provide credential_id or fill password (fallback).")
        return username, password

    def _imap_connect(self, input_data: NodeExecutionInput) -> imaplib.IMAP4_SSL:
        host, port = self._resolve_imap_settings()
        username, password = self._get_auth_from_credentials(input_data)
        client = imaplib.IMAP4_SSL(host, port)
        client.login(username, password)
        return client

    def _imap_select_folder(self, client: imaplib.IMAP4_SSL, folder: str) -> None:
        mailbox = self._quote_mailbox(folder)
        status, _ = client.select(mailbox)
        if status != "OK":
            raise RuntimeError(f"Failed to select folder '{folder}' on IMAP server (status={status}).")

    def _imap_login_and_select(self, input_data: NodeExecutionInput) -> Tuple[imaplib.IMAP4_SSL, str]:
        client = self._imap_connect(input_data)
        folder = self._resolve_folder()
        self._imap_select_folder(client, folder)
        return client, folder

    def _imap_noop(self, client: imaplib.IMAP4_SSL) -> None:
        client.noop()

    @staticmethod
    def _imap_since_date_str(dt_utc: datetime) -> str:
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        return f"{dt_utc.day:02d}-{months[dt_utc.month - 1]}-{dt_utc.year}"

    def _imap_search(self, client: imaplib.IMAP4_SSL, activation_time: datetime) -> List[bytes]:
        mode = (self.config.get("search_mode") or "all").lower().strip()
        use_since = bool(self.config.get("use_since_optimization", True))

        criteria: List[str] = []
        if mode == "unseen":
            criteria.append("UNSEEN")
        elif mode == "recent":
            criteria.append("RECENT")
        else:
            criteria.append("ALL")

        if use_since:
            criteria.append("SINCE")
            criteria.append(self._imap_since_date_str(activation_time))

        status, data = client.search(None, *criteria)
        if status != "OK" or not data or not data[0]:
            return []
        return data[0].split()

    def _imap_fetch_message(self, client: imaplib.IMAP4_SSL, msg_id: bytes) -> email.message.Message:
        status, data = client.fetch(msg_id, "(RFC822)")
        if status != "OK" or not data:
            raise RuntimeError("IMAP fetch failed.")
        raw = None
        for item in data:
            if isinstance(item, tuple) and len(item) >= 2:
                raw = item[1]
                break
        if raw is None:
            raise RuntimeError("No RFC822 payload returned by IMAP server.")
        return email.message_from_bytes(raw)

    def _imap_mark_seen(self, client: imaplib.IMAP4_SSL, msg_id: bytes) -> None:
        client.store(msg_id, "+FLAGS", "\\Seen")

    # -------------------------
    # Email parsing/filtering
    # -------------------------

    @staticmethod
    def _decode_mime_header(value: Optional[str]) -> str:
        if not value:
            return ""
        parts = decode_header(value)
        decoded: List[str] = []
        for text, enc in parts:
            if isinstance(text, bytes):
                try:
                    decoded.append(text.decode(enc or "utf-8", errors="replace"))
                except Exception:
                    decoded.append(text.decode("utf-8", errors="replace"))
            else:
                decoded.append(text)
        return "".join(decoded).strip()

    @staticmethod
    def _parse_email_date(msg: email.message.Message) -> Optional[datetime]:
        date_hdr = msg.get("Date")
        if not date_hdr:
            return None
        try:
            dt = parsedate_to_datetime(date_hdr)
            if dt is None:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None

    @staticmethod
    def _extract_bodies(msg: email.message.Message) -> Dict[str, Any]:
        text_parts: List[str] = []
        html_parts: List[str] = []

        def decode_payload(part: email.message.Message) -> str:
            payload = part.get_payload(decode=True)
            if payload is None:
                return ""
            charset = part.get_content_charset() or "utf-8"
            try:
                return payload.decode(charset, errors="replace")
            except Exception:
                return payload.decode("utf-8", errors="replace")

        if msg.is_multipart():
            for part in msg.walk():
                ctype = (part.get_content_type() or "").lower()
                disp = (part.get("Content-Disposition") or "").lower()
                if "attachment" in disp:
                    continue
                if ctype == "text/plain":
                    content = decode_payload(part).strip()
                    if content:
                        text_parts.append(content)
                elif ctype == "text/html":
                    content = decode_payload(part).strip()
                    if content:
                        html_parts.append(content)
        else:
            ctype = (msg.get_content_type() or "").lower()
            if ctype == "text/plain":
                content = decode_payload(msg).strip()
                if content:
                    text_parts.append(content)
            elif ctype == "text/html":
                content = decode_payload(msg).strip()
                if content:
                    html_parts.append(content)

        return {"text": "\n\n".join(text_parts).strip(), "html": "\n\n".join(html_parts).strip()}

    @staticmethod
    def _strip_html_basic(html_text: str) -> str:
        if not html_text:
            return ""
        out = []
        in_tag = False
        for ch in html_text:
            if ch == "<":
                in_tag = True
                continue
            if ch == ">":
                in_tag = False
                continue
            if not in_tag:
                out.append(ch)
        return " ".join("".join(out).split()).strip()

    def _extract_main_message(self, body_text: str) -> str:
        """Extract the main message from email body, ignoring reply chains."""
        if not body_text:
            return ""
        lines = body_text.split('\n')
        main_message = ""
        for line in lines:
            line = line.strip()
            if line and not line.startswith('>') and not line.lower().startswith('on ') and not 'wrote:' in line.lower():
                main_message = line
                break
        return main_message

    def _matches_filters(self, input_data: NodeExecutionInput, sender: str, subject: str) -> bool:
        from app.core.nodes.variables import resolve_config_value
        
        from_filter_raw = input_data.config.get("from_filter") or ""
        from_filter = resolve_config_value(from_filter_raw, input_data.variables).strip().lower()
        
        subj_filter_raw = input_data.config.get("subject_contains") or ""
        subj_filter = resolve_config_value(subj_filter_raw, input_data.variables).strip().lower()
        
        if from_filter and from_filter not in (sender or "").lower():
            return False
        if subj_filter and subj_filter not in (subject or "").lower():
            return False
        return True

    # -------------------------
    # Execution
    # -------------------------

    async def execute(self, input_data: NodeExecutionInput):
        context = (input_data.ports or {}).get("context")

        polling_interval = int(self.config.get("polling_interval_seconds") or 5)
        if polling_interval < 1:
            polling_interval = 1

        timeout_seconds = int(self.config.get("timeout_seconds") or 0)
        reconnect_on_error = bool(self.config.get("reconnect_on_error", True))
        noop_every = int(self.config.get("noop_keepalive_every_polls") or 0)
        max_candidates = int(self.config.get("max_candidates_per_poll") or 0)
        mark_as_read = bool(self.config.get("mark_as_read", False))

        only_after_activation = bool(self.config.get("only_after_activation", True))
        log_candidates = bool(self.config.get("log_candidate_headers", False))
        log_skips_before = bool(self.config.get("log_skips_before_activation", False))

        activation_time = datetime.now(timezone.utc)
        start_monotonic = asyncio.get_running_loop().time()

        host, port = self._resolve_imap_settings()
        folder = self._resolve_folder()
        search_mode = (self.config.get("search_mode") or "all").lower().strip()
        poll_level = self._poll_level()

        self._log(
            logging.INFO,
            f"[EmailListener] Start workflow_id={input_data.workflow_id} execution_id={input_data.execution_id} node_id={input_data.node_id}",
        )
        self._log(
            logging.INFO,
            f"[EmailListener] Activation(UTC)={activation_time.isoformat()} imap={host}:{port} folder='{folder}' search_mode={search_mode} polling={polling_interval}s timeout={timeout_seconds}s",
        )
        from app.core.nodes.variables import resolve_config_value
        
        from_filter_resolved = resolve_config_value(input_data.config.get("from_filter") or "", input_data.variables)
        subj_filter_resolved = resolve_config_value(input_data.config.get("subject_contains") or "", input_data.variables)
        
        if from_filter_resolved or subj_filter_resolved:
            self._log(
                logging.INFO,
                f"[EmailListener] Filters from_contains='{from_filter_resolved or ''}' subject_contains='{subj_filter_resolved or ''}'",
            )
        self._log(
            logging.INFO,
            f"[EmailListener] only_after_activation={only_after_activation} use_since_optimization={bool(self.config.get('use_since_optimization', True))} max_candidates_per_poll={max_candidates}",
        )

        client: Optional[imaplib.IMAP4_SSL] = None
        poll_count = 0

        async def connect() -> Tuple[imaplib.IMAP4_SSL, str]:
            c, f = await asyncio.to_thread(self._imap_login_and_select, input_data)
            return c, f

        async def reconnect(reason: str) -> None:
            nonlocal client
            self._log(logging.WARNING, f"[EmailListener] Reconnecting IMAP (reason: {reason})")
            try:
                if client is not None:
                    await asyncio.to_thread(client.logout)
            except Exception:
                pass
            client = None
            await asyncio.sleep(min(polling_interval, 2))
            client, _ = await connect()

        try:
            client, _ = await connect()

            while True:
                poll_count += 1

                if timeout_seconds > 0:
                    elapsed = asyncio.get_running_loop().time() - start_monotonic
                    if elapsed >= timeout_seconds:
                        self._log(logging.WARNING, f"[EmailListener] Timeout after {int(elapsed)}s waiting for matching email.")
                        raise TimeoutError("Email Listener timed out waiting for a matching email.")

                if noop_every > 0 and (poll_count % noop_every == 0):
                    try:
                        await asyncio.to_thread(self._imap_noop, client)
                    except Exception as e:
                        if reconnect_on_error:
                            await reconnect(f"NOOP failed: {e}")
                        else:
                            raise

                try:
                    msg_ids = await asyncio.to_thread(self._imap_search, client, activation_time)
                except Exception as e:
                    self._log(logging.ERROR, f"[EmailListener] IMAP search failed on poll #{poll_count}: {e}")
                    if reconnect_on_error:
                        await reconnect(f"search failed: {e}")
                        continue
                    await asyncio.sleep(polling_interval)
                    continue

                if poll_level is not None:
                    self._log(poll_level, f"[EmailListener] Poll #{poll_count}: candidates={len(msg_ids)} mode={search_mode}")

                msg_ids_iter = list(reversed(msg_ids))
                if max_candidates > 0:
                    msg_ids_iter = msg_ids_iter[:max_candidates]

                for msg_id in msg_ids_iter:
                    try:
                        msg = await asyncio.to_thread(self._imap_fetch_message, client, msg_id)
                    except Exception:
                        continue

                    subject = self._decode_mime_header(msg.get("Subject"))
                    sender = self._decode_mime_header(msg.get("From"))
                    msg_dt = self._parse_email_date(msg)

                    if log_candidates and poll_level is not None:
                        hdr_date = self._decode_mime_header(msg.get("Date"))
                        hdr_mid = self._decode_mime_header(msg.get("Message-ID"))
                        self._log(
                            poll_level,
                            f"[EmailListener] Candidate msg_id={msg_id!r} From='{sender}' Subject='{subject}' Date='{hdr_date}' Message-ID='{hdr_mid}' parsed_utc='{(msg_dt.isoformat() if msg_dt else None)}'",
                        )

                    if only_after_activation:
                        if msg_dt is None:
                            if log_skips_before and poll_level is not None:
                                self._log(poll_level, f"[EmailListener] Skip msg_id={msg_id!r}: Date not parseable (required for activation gate).")
                            continue
                        if msg_dt <= activation_time:
                            if log_skips_before and poll_level is not None:
                                self._log(
                                    poll_level,
                                    f"[EmailListener] Skip msg_id={msg_id!r}: msg_dt={msg_dt.isoformat()} <= activation={activation_time.isoformat()}",
                                )
                            continue

                    if not self._matches_filters(input_data, sender=sender, subject=subject):
                        continue

                    bodies = self._extract_bodies(msg)
                    content = bodies.get("text") or self._strip_html_basic(bodies.get("html", ""))

                    # Clean the body_text to extract main message
                    cleaned_body_text = self._extract_main_message(bodies.get("text", ""))

                    email_data = {
                        "subject": subject,
                        "from": sender,
                        "to": self._decode_mime_header(msg.get("To")),
                        "cc": self._decode_mime_header(msg.get("Cc")),
                        "date": (msg_dt.isoformat() if msg_dt else None),
                        "message_id": self._decode_mime_header(msg.get("Message-ID")),
                        "headers": {k: self._decode_mime_header(v) for (k, v) in msg.items()},
                        "body_text": cleaned_body_text,
                        "body_html": bodies.get("html", ""),
                    }

                    self._log(
                        logging.INFO,
                        f"[EmailListener] MATCH msg_id={msg_id!r} date_utc={(msg_dt.isoformat() if msg_dt else None)} From='{sender}' Subject='{subject}'",
                    )

                    if mark_as_read:
                        try:
                            await asyncio.to_thread(self._imap_mark_seen, client, msg_id)
                        except Exception as e:
                            self._log(logging.WARNING, f"[EmailListener] Failed to mark as read msg_id={msg_id!r}: {e}")

                    return {
                        "email": cleaned_body_text,  # Simplified to just the main message
                        "subject": subject,
                        "sender": sender,
                        "content": cleaned_body_text,  # Use cleaned message
                        "context": context,
                    }

                await asyncio.sleep(polling_interval)

        finally:
            if client is not None:
                try:
                    await asyncio.to_thread(client.logout)
                except Exception:
                    pass