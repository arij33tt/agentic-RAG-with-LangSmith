import logging 
from supabase import create_client , Client
from src.config.settings import settings

logger = logging.getLogger(__name__) # python ka variable h , jo tells which file is generating the logs 


_supabase_client: Client | None = None


def get_supabase_client() -> Client :
    """ returns a single shared Supabase Client Inst.
    Creates it once on first call , re uses it on every call 
     singleton 
    """
    global _supabase_client
    
    if _supabase_client is None:
        try:
            _supabase_client= create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY,
                
            )
            logger.info("Supabase Client Initialized succ.")
        except Exception as e :
            logger.info(f"failed to Create Supabase Cilent {e}")
            raise 
    return _supabase_client


supabase= get_supabase_client()
            
    
    
    