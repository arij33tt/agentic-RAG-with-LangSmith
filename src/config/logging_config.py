import logging
import contextvars
from pythonjsonlogger import jsonlogger
from src.config.settings import settings


# holds values for each different requests 
request_id_var : contextvars.ContextVar[str]=contextvars.ContextVar("request_id",default="-")
tenant_id_var: contextvars.ContextVar[str]=contextvars.ContextVar("tenant_id",default="-")
user_id_var: contextvars.ContextVar[str]=contextvars.ContextVar("user_id",default="-")


class ContextFilter(logging.Filter): # bridge btw contextVars and logging system
    """injects the current req. context vars into every log record """
    
    def filter(self ,record:logging.LogRecord)->bool :
        record.request_id=request_id_var.get()
        record.user_id= user_id_var.get()
        record.tenant_id= tenant_id_var.get()
        return True
 
 
    
def configure_logging() -> None:
    """Call this once,"""

    log_level = logging.DEBUG if settings.environment == "dev" else logging.INFO #fail loud in dev, quiet in prod

    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s "
            "%(request_id)s %(tenant_id)s %(user_id)s",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "name": "logger",
        },
    )
    handler.setFormatter(formatter)
    handler.addFilter(ContextFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = [handler] 
