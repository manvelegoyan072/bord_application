from transitions.extensions.asyncio import AsyncMachine
from app.models.tenders import Tender
from app.core.logging_config import logger

class TenderStateMachine:
    states = [
        "RECEIVED",
        "VALIDATING",
        "VALIDATION_FAILED",
        "FETCHING_DOCUMENTS",
        "DOCUMENTS_NOT_FOUND",
        "SCRAPING_DOCUMENTS",
        "DOCUMENTS_FETCH_FAILED",
        "DOCUMENTS_SAVED",
        "FILTERING",
        "REJECTED_FILTER",
        "AI_PROCESSING",
        "REJECTED_AI",
        "READY_FOR_EXPORT",
        "EXPORTING",
        "COMPLETED",
        "EXPORT_FAILED",
        "ERROR"
    ]

    def __init__(self, tender: Tender, tender_id: str):
        self.tender = tender
        self.tender_id = tender_id
        self.machine = AsyncMachine(
            model=self,
            states=TenderStateMachine.states,
            initial=tender.state or "RECEIVED",
            queued=True,
            send_event=True
        )

        self.machine.add_transition("start_validating", "RECEIVED", "VALIDATING")
        self.machine.add_transition("fail_validation", "VALIDATING", "VALIDATION_FAILED")
        self.machine.add_transition("fetch_documents", "VALIDATING", "FETCHING_DOCUMENTS")
        self.machine.add_transition("documents_not_found", "FETCHING_DOCUMENTS", "DOCUMENTS_NOT_FOUND")  # Исправлено
        self.machine.add_transition("save_documents", "FETCHING_DOCUMENTS", "DOCUMENTS_SAVED")
        self.machine.add_transition("start_scraping", "DOCUMENTS_NOT_FOUND", "SCRAPING_DOCUMENTS")
        self.machine.add_transition("fail_scraping", "SCRAPING_DOCUMENTS", "DOCUMENTS_FETCH_FAILED")
        self.machine.add_transition("finish_scraping", "SCRAPING_DOCUMENTS", "DOCUMENTS_SAVED")
        self.machine.add_transition("start_filtering", "DOCUMENTS_SAVED", "FILTERING")
        self.machine.add_transition("reject_after_filtering", "FILTERING", "REJECTED_FILTER")
        self.machine.add_transition("start_ai", "FILTERING", "AI_PROCESSING")
        self.machine.add_transition("reject_after_ai", "AI_PROCESSING", "REJECTED_AI")
        self.machine.add_transition("prepare_export", "AI_PROCESSING", "READY_FOR_EXPORT")
        self.machine.add_transition("start_exporting", "READY_FOR_EXPORT", "EXPORTING")
        self.machine.add_transition("complete", "EXPORTING", "COMPLETED")
        self.machine.add_transition("fail_export", "EXPORTING", "EXPORT_FAILED")
        self.machine.add_transition("encounter_error", "*", "ERROR")

    async def on_enter_RECEIVED(self, event):
        logger.info(f"Tender {self.tender_id} entered state RECEIVED")

    async def on_enter_VALIDATING(self, event):
        logger.info(f"Tender {self.tender_id} entered state VALIDATING")

    async def on_enter_VALIDATION_FAILED(self, event):
        logger.info(f"Tender {self.tender_id} entered state VALIDATION_FAILED")

    async def on_enter_FETCHING_DOCUMENTS(self, event):
        logger.info(f"Tender {self.tender_id} entered state FETCHING_DOCUMENTS")

    async def on_enter_DOCUMENTS_NOT_FOUND(self, event):
        logger.info(f"Tender {self.tender_id} entered state DOCUMENTS_NOT_FOUND")

    async def on_enter_SCRAPING_DOCUMENTS(self, event):
        logger.info(f"Tender {self.tender_id} entered state SCRAPING_DOCUMENTS")

    async def on_enter_DOCUMENTS_FETCH_FAILED(self, event):
        logger.info(f"Tender {self.tender_id} entered state DOCUMENTS_FETCH_FAILED")

    async def on_enter_DOCUMENTS_SAVED(self, event):
        logger.info(f"Tender {self.tender_id} entered state DOCUMENTS_SAVED")

    async def on_enter_FILTERING(self, event):
        logger.info(f"Tender {self.tender_id} entered state FILTERING")

    async def on_enter_REJECTED_FILTER(self, event):
        logger.info(f"Tender {self.tender_id} entered state REJECTED_FILTER")

    async def on_enter_AI_PROCESSING(self, event):
        logger.info(f"Tender {self.tender_id} entered state AI_PROCESSING")

    async def on_enter_REJECTED_AI(self, event):
        logger.info(f"Tender {self.tender_id} entered state REJECTED_AI")

    async def on_enter_READY_FOR_EXPORT(self, event):
        logger.info(f"Tender {self.tender_id} entered state READY_FOR_EXPORT")

    async def on_enter_EXPORTING(self, event):
        logger.info(f"Tender {self.tender_id} entered state EXPORTING")

    async def on_enter_COMPLETED(self, event):
        logger.info(f"Tender {self.tender_id} entered state COMPLETED")

    async def on_enter_EXPORT_FAILED(self, event):
        logger.info(f"Tender {self.tender_id} entered state EXPORT_FAILED")

    async def on_enter_ERROR(self, event):
        logger.info(f"Tender {self.tender_id} entered state ERROR")