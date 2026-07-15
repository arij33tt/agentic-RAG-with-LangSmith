import logging 
import io 
import requests
from  abc import ABC,abstractmethod
from pypdf import PdfReader
import pymupdf
from docx import Document as DocxDocument
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class LoaderError(Exception):
    """Document cannot be loaded/parsedd"""
    pass


class BaseLoader(ABC):
    """Contract every loader must follow"""
    
    @abstractmethod
    def load(self,source:bytes|str)->str:
        """Returns plain extracted text from the raw source."""
        raise NotImplementedError
    
class PDFLoader(BaseLoader):
    
    def load(self,source:bytes|str)->str:
        try:
            reader = PdfReader(io.BytesIO(source))
            pages_text=[]
            
            for page_num , page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    pages_text.append(text)
                else:
                    logger.warning(f"No extractable text on page {page_num} (possibly scanned/image-only)")
                
            return "\n\n".join (pages_text)
        
        except Exception as e:
            raise LoaderError(f" failed to load the {source} pdf {e}") from e 


class DocxLoader(BaseLoader):
    def load(self,source:bytes|str)-> str:
        try:
            doc = DocxDocument(io.BytesIO(source))
            
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip() ]
            
            return "\n\n".join(paragraphs)
        
        
        
        except Exception as e :
            raise LoaderError(f"failed to load the {source} doc {e}") from e 
        
        
class HTMLLoader(BaseLoader):
    def load(self,source:bytes|str)->str:
        
        try:
            html_content= source if isinstance(source,str) else source.decode("utf-8",errors="ignore")
            soup = BeautifulSoup(html_content, "html.parser")
            
            
            # remove elements that are never real content
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
                
            text = soup.get_text(separator="\n")
            
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            
            return "\n\n".join(lines)
        
        except Exception as e:
            raise LoaderError(f" Error Loading/parsing html content {e}") from e 


class URLLoader(BaseLoader):
    def __init__(self, timeout_seconds: int = 20):
        self.timeout_seconds = timeout_seconds
        self.html_loader = HTMLLoader()
        
        
    def load(self, source: bytes | str) -> str:
        
        try:
            
            response = requests.get(source,timeout=self.timeout_seconds)
            response.raise_for_status()
        except Exception as e:
            raise LoaderError(f" failed to fetch url {source} {e}")from e 

        
        return self.html_loader.load(response.text)



class TextLoader(BaseLoader):
    def load (self , source:bytes|str)-> str:
        if isinstance(source,bytes):
            return source.decode("utf-8",errors="ignore")
        
        return source
    
    

            
            
            
        
        
                
            

