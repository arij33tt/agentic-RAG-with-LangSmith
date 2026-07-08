# # # test_settings.py (delete after confirming)
# # from src.config.settings import settings

# # print(settings.SUPABASE_URL)
# # print(settings.SUPABASE_SERVICE_KEY)
# # print(settings.environment)

# # # test_chunk_schema.py (delete after confirming)
# # from src.schemas.chunk_schema import ChunkCreate
# # from uuid import uuid4

# # # valid case
# # chunk = ChunkCreate(
# #     document_id=uuid4(),
# #     tenant_id=uuid4(),
# #     content="This is a test chunk about refund policy.",
# #     chunk_index=0,
# #     token_count=10,
# # )
# # print(chunk)

# # # invalid case — should raise an error
# # try:
# #     bad_chunk = ChunkCreate(
# #         document_id=uuid4(),
# #         tenant_id=uuid4(),
# #         content="hello suno na ",   # blank after stripping
# #         chunk_index=0,
# #         token_count=10,
# #     )
# # except Exception as e:
#     # print("Correctly rejected:", e)
    
    
# from src.schemas.document_schema import DocumentCreate
# from src.schemas.query_schema import UserQuery
# from uuid import uuid4
# import hashlib

# # document test
# doc = DocumentCreate(
#     tenant_id=uuid4(),
#     title="Refund Policy 2026",
#     source_type="pdf",
#     checksum=hashlib.sha256(b"fake file bytes").hexdigest(),
# )
# print(doc)

# # query test
# q = UserQuery(
#     question="What is the refund policy for international orders?",
#     tenant_id=uuid4(),
#     user_id=uuid4(),
# )
# print(q)


# test_remaining_schemas.py (delete after confirming)
from src.schemas.response_schema import AgentResponse, Citation
from src.schemas.agent_state_schema import AgentStateValidator
from uuid import uuid4

# should succeed
resp = AgentResponse(
    answer="Refunds are processed within 5-7 business days.",
    used_retrieval=True,
    citations=[Citation(
        chunk_id=uuid4(), document_id=uuid4(),
        document_title="Refund Policy 2026",
        snippet="Refunds are processed within 5-7 business days of approval.",
    )],
    grounded=True,
    conversation_id=uuid4(),
    latency_ms=842,
)
print(resp)

# should fail — claims retrieval but no citations
try:
    bad_resp = AgentResponse(
        answer="Refunds are processed within 5-7 business days.",
        used_retrieval=True,
        citations=[],
        grounded=True,
        conversation_id=uuid4(),
        latency_ms=842,
    )
except Exception as e:
    print("Correctly rejected:", e)

state = AgentStateValidator(question="test", tenant_id=uuid4())
print(state)