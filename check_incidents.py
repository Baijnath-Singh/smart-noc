import chromadb

c = chromadb.HttpClient(host='localhost', port=8000)
coll = c.get_collection('incidents')

print(f"Total incidents: {coll.count()}\n")

res = coll.get(limit=2, include=['documents', 'metadatas'])

for i in range(len(res['ids'])):
    print(f"ID: {res['ids'][i]}")
    print(f"Type: {res['metadatas'][i].get('incident_type')}")
    print(f"Vendor: {res['metadatas'][i].get('vendor')}")
    print(f"Severity: {res['metadatas'][i].get('severity')}")
    print(f"Text:\n{res['documents'][i]}")
    print("-" * 80)
