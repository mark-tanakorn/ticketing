"""
Communication Nodes

Nodes for email, webhooks, HTTP requests, and other communication channels.
"""

# Import nodes to trigger registration
from app.core.nodes.builtin.communication.email_composer import EmailComposerNode
from app.core.nodes.builtin.communication.email_approval import EmailApprovalNode
from app.core.nodes.builtin.communication.whatsapp_send import WhatsAppSendNode
from app.core.nodes.builtin.communication.whatsapp_listener import WhatsAppListenerNode

__all__ = [
    "EmailComposerNode",
    "EmailApprovalNode",
    "WhatsAppSendNode",
    "WhatsAppListenerNode",
]

