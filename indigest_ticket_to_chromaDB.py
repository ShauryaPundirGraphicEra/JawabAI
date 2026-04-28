import csv
import chromadb

def ingest_tickets():
    print("Initializing ChromaDB...")
    # 1. Setup local persistent database
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_or_create_collection(name="ticket_history")

    documents = []
    metadatas = []
    ids = []

    print("Reading synthetic_tickets.csv...")
    # 2. Parse the CSV
    try:
        with open('synthetic_tickets.csv', mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # We embed the Title + Description so similarity search hits both
                doc_text = f"Title: {row['title']} | Description: {row['description']}"
                documents.append(doc_text)
                
                # We store the resolution in metadata so the LLM can use it later
                metadatas.append({
                    "resolution": row['resolution'],
                    "category": row['category'],
                    "priority": row['priority'],
                    
                })
                
                ids.append(row['ticket_id'])
    except FileNotFoundError:
        print("ERROR: Could not find 'synthetic_tickets.csv'. Please make sure it is in the same folder.")
        return

    # 3. Batch insert into ChromaDB (Batching prevents crashing)
    batch_size = 100
    total_docs = len(documents)
    
    print(f"Found {total_docs} tickets. Starting embedding process (this might take a minute)...")
    
    for i in range(0, total_docs, batch_size):
        end_idx = min(i + batch_size, total_docs)
        print(f"Upserting batch {i} to {end_idx}...")
        collection.add(
            documents=documents[i:end_idx],
            metadatas=metadatas[i:end_idx],
            ids=ids[i:end_idx]
        )

    print("\n SUCCESS! Database populated and saved to the './chroma_db' folder.")
    print("Node 3C (RAG Retrieval) is now fully armed.")

if __name__ == "__main__":
    ingest_tickets()