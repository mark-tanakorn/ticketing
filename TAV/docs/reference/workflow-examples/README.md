## Workflow examples (sanitized)

This folder contains **sanitized, editor-compatible workflow JSON examples** used to ground the Builder's workflow-draft generation.

### Sanitization rules used
- **IDs**: Workflow `id` and node `node_id` values are replaced with stable, human-readable IDs like `n_whatsapp_send_approver`.
- **Secrets**: Any secrets/tokens/passwords are replaced with safe placeholders or empty strings.
  - Examples: `"password": "<ENCRYPTED_PASSWORD>"`, `"auth_token": "<TOKEN>"`, `"bot_token": "<TELEGRAM_BOT_TOKEN>"`
- **Credentials**: `credential_id` values are replaced with small non-sensitive integers (e.g. `1`) to keep JSON type-stable.
- **Emails / phone numbers / personal names**: Replaced with `example.com` placeholders.
- **Network paths / IPs / internal hosts**: Replaced with `\\\\SERVER\\Share\\Path` or `https://api.example.com/...`.
- **File references**: `file_id`, `template_file` replaced with descriptive placeholders like `"FILE_ID_TEMPLATE_PDF"`.

### Notes for the LLM
- These examples are **reference**; do not copy IDs verbatim into drafts.
- Prefer matching the **shape**: nodes array, connections array, canvas_objects, ports, categories, icons, config keys.
- Use `node_id`/`node_type` (not `id`/`type`) and `connection_id`/`source_node_id`/`target_node_id`.


