import chromadb
from sentence_transformers import SentenceTransformer

# Connect to ChromaDB
c = chromadb.HttpClient(host='chromadb', port=8000)
coll = c.get_collection('incidents')

# Load same model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Test query (similar to what diagnosis_service builds)
test_query = "DEVICE FAILURE device core-router-01 MEDIUM"
print(f"Query: {test_query}\n")

# Generate embedding
query_embedding = model.encode(test_query).tolist()

# Search WITHOUT filters first
results = coll.query(
    query_embeddings=[query_embedding],
    n_results=5
)

print("=== SEARCH RESULTS (No Filters) ===")
for i in range(len(results['ids'][0])):
    similarity = 1 - results['distances'][0][i]
    print(f"\n{i+1}. ID: {results['ids'][0][i]}")
    print(f"   Similarity: {similarity:.4f}")
    print(f"   Type: {results['metadatas'][0][i].get('incident_type')}")
    print(f"   Vendor: {results['metadatas'][0][i].get('vendor')}")
    print(f"   Text: {results['documents'][0][i][:150]}...")

# Now with filter
print("\n\n=== SEARCH RESULTS (With Filter: incident_type=DEVICE_FAILURE) ===")
results_filtered = coll.query(
    query_embeddings=[query_embedding],
    n_results=5,
    where={"incident_type": "DEVICE_FAILURE"}
)

for i in range(len(results_filtered['ids'][0])):
    similarity = 1 - results_filtered['distances'][0][i]
    print(f"\n{i+1}. ID: {results_filtered['ids'][0][i]}")
    print(f"   Similarity: {similarity:.4f}")
    print(f"   Threshold Check: {'PASS' if similarity >= 0.6 else 'FAIL (< 0.6)'}")
