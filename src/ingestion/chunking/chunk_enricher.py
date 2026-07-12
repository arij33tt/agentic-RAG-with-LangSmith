import logging 
from uuid import UUID 
from src.schemas.chunk_schema import ChunkCreate
from src.database.supabase_client import supabase

logger = logging.getLogger(__name__)

class ChunkEnricher():
    """ 
    takes raw chunks from chunkers and enrich them with 
    
    1.) contextual headers ( shorts summy of where the chunks sits )
    2>) Patent-chunk links (groups small chunks into large chuks )
     
    """
    
    def __init__ (self , llm_client,group_size=4):
        """"
        group_size - > size of parent chunk ( no. of child chunks merged for parent chunk)
        
        llm_client - > 
        
        """
        self.llm_client= llm_client
        self.group_size = group_size
    
    def add_contextual_headers(self, chunks:list[ChunkCreate],document_title:str)->list[ChunkCreate]:
        
        """
        prepends short llm genereated summary of chunks context , before embeddings , Improves retrieval accuracy 
        """
        
        enriched:list[ChunkCreate]
        
        for chunk in chunks:
            try:
                header = self._generate_context_header(document_title,chunk.content)
                new_content = f"{header} \n\n{chunk.content}"
                enriched_chunk = chunk.model_copy(update={"content":new_content})   
                enriched.append(enriched_chunk)
                
            except Exception as e:
                logger.warning (f"Context header generation failed, using raw chunk: {e}")
                enriched.append(chunk)     
        
        return enriched
    
    def _generate_context_header(self,document_title:str,chunk_text:str) -> str:
        prompt=(
            f"Document: {document_title}\n\n"
            f"Chunk:\n{chunk_text}\n\n"
            "Write ONE short sentence (max 25 words) describing what section "
            "of the document this chunk is from, to give it context. "
            "Output only the sentence, nothing else."
        )
        
        return self.llm_client.generate(prompt).strip()
    
    #  now adding parent chunk to child chunk 
    
    def create_parent_chunk_links(self,child_chunks:list[ChunkCreate])-> tuple[list[ChunkCreate],list[ChunkCreate]]:
        """group every `grup_size` consect. child chunks into one large parent chunk 
            return parent_chunk, updated child chunks .
            
        """
        
        parent_chunks:list[ChunkCreate]=[]
        updated_children:list[ChunkCreate]=[]
        
        for i in range (0,len(child_chunks),self.group_size):
            group= child_chunks[i:i+self.group_size]
            
            merged_content = "\n\n".join( c.content for c in group)
            
            parent = ChunkCreate(
                document_id = group[0].document_id,
                tenant_id = group[0].tenant_id,
                content= merged_content,
                chunk_index= i // self.group_size,
                token_count = sum(c.token_count for c in group),
                section_path =group[0].section_path
                
            )
            
            parent_chunks.append(parent)
            
            updated_children.extend(group)
            
        return parent_chunks,updated_children
    def attach_parent_ids(self,child_chunks:list[ChunkCreate],inserted_parent_ids:list[UUID])->list[ChunkCreate]:
        
        """ 
        called after parent_chunk is inserted in to supabase and theri real ids are know to add to child_chunks , sets parent_chunk_id to chuild 
        
        """
        
        updated:list[ChunkCreate]=[]
        
        for i , child in enumerate(child_chunks):
            parent_index = i // self.group_size
            parent_id = inserted_parent_ids[parent_index]
            updated_child = child.model_copy(update={"parent_chunk_id": parent_id})
            updated.append(updated_child)
            
        return updated
    
    
    
            
        
        
        
        
        
            
        
        
        
        