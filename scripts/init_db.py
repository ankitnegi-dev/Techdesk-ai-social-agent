import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.db.models import init_db, AsyncSessionLocal
from services.rag.pipeline import add_knowledge_chunk
from services.rlhf.collector import PreferencePair
from shared.audit import AuditLog

async def main():
    print("Creating database tables...")
    await init_db()

    print("Seeding TechDesk AI knowledge base...")
    async with AsyncSessionLocal() as db:
        faqs = [
            ("Getting started with TechDesk AI", "To get started, sign up at app.techdesk.ai and complete the 3-step onboarding. First connect your support inbox, then invite your team, then set up your first AI response template. The whole setup takes under 10 minutes.", "onboarding"),
            ("Supported integrations", "TechDesk AI integrates with Gmail, Outlook, Slack, Zendesk, Intercom, HubSpot, Salesforce, Jira, and 40+ other tools. Find the full list under Settings > Integrations. New integrations are added every month.", "integrations"),
            ("Pricing plans", "TechDesk AI offers three plans: Starter (free, up to 3 agents, 100 tickets/month), Growth ($49/month, up to 10 agents, unlimited tickets), and Enterprise (custom pricing, unlimited agents, dedicated support). All plans include a 14-day free trial with no credit card required.", "pricing"),
            ("AI response accuracy", "TechDesk AI learns from your past tickets and knowledge base. Accuracy improves over time — most teams see 85%+ accuracy after 2 weeks of use. You can always edit or reject AI suggestions before they are sent.", "product"),
            ("Data security and privacy", "All data is encrypted at rest (AES-256) and in transit (TLS 1.3). TechDesk AI is SOC 2 Type II certified and GDPR compliant. Your data is never used to train models for other customers. You can export or delete all data at any time.", "security"),
            ("API access and documentation", "The TechDesk AI REST API is available on Growth and Enterprise plans. Generate your API key at Settings > Developer > API Keys. Full documentation, SDKs for Python, Node.js, and Ruby are available at docs.techdesk.ai/api.", "developer"),
            ("Cancellation and refund policy", "You can cancel your subscription anytime from Settings > Billing > Cancel Plan. Cancellations take effect at the end of the current billing period. We offer a full refund within 7 days of your first payment if you are not satisfied.", "billing"),
            ("Response time and support", "TechDesk AI support responds within 2 hours on weekdays and within 24 hours on weekends. Enterprise customers get a dedicated success manager and 24/7 priority support. Use the in-app chat for the fastest response.", "support"),
            ("Team collaboration features", "Multiple agents can work together on tickets. Features include ticket assignment, internal notes, collision detection, shared canned responses, and team performance analytics.", "product"),
            ("Mobile app", "The TechDesk AI mobile app is available on iOS App Store and Android Google Play. Search for TechDesk AI. The app supports ticket management, AI suggestions, push notifications, and team chat.", "product"),
            ("Resetting password", "To reset your password, click Forgot Password on the login page and enter your email. You will receive a reset link within 2 minutes. Check your spam folder if you do not see it.", "account"),
            ("Ticket automation rules", "Create automation rules under Settings > Automation. You can auto-assign tickets by keyword, customer tier, or source. Most teams save 3-4 hours per day with automations.", "product"),
        ]
        for title, content, category in faqs:
            await add_knowledge_chunk(db, title, content, category)
        print(f"Added {len(faqs)} TechDesk AI knowledge base entries")

    print("Done! TechDesk AI is ready.")

asyncio.run(main())
