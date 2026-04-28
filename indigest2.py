import pandas as pd
import chromadb

def ingest_tickets():
    print("Initializing ChromaDB...")
    # 1. Setup local persistent database
    client = chromadb.PersistentClient(path="./chroma_db")
    
    # BEST PRACTICE: Use a new collection name for the new schema to avoid metadata collisions
    collection_name = "ticket_history"
    collection = client.get_or_create_collection(name=collection_name)

    documents = []
    metadatas = []
    ids = []

    # Update this to match your downloaded file's name
    dataset_filename = 'tickets.xlsx' 
    print(f"Reading {dataset_filename}...")

    # 2. Parse the Excel file using pandas
    try:
        # Read the Excel file
        df = pd.read_excel(dataset_filename)

        # Loop through each row in the DataFrame
        for idx, row in df.iterrows():
            subject = str(row.get('subject', '')).strip()
            body = str(row.get('body', '')).strip()
            
            # Skip empty rows
            if not subject and not body:
                continue

            # We embed the Subject + Body for the similarity search
            doc_text = f"Subject: {subject} | Body: {body}"
            documents.append(doc_text)
            
            # Dynamically collect tag_1 through tag_8, ignoring empty cells
            tags = []
            for i in range(1, 9):
                tag_val = str(row.get(f'tag_{i}', '')).strip()
                if tag_val:
                    tags.append(tag_val)
            
            # Store the rich ITIL metadata so we can filter by it later in LangGraph
            metadatas.append({
                "resolution": str(row.get('answer', '')).strip(),
                "queue": str(row.get('queue', '')).strip(),
                "type": str(row.get('type', '')).strip(),
                "priority": str(row.get('priority', '')).strip(),
                "tags": ", ".join(tags)  # Chroma requires metadata values to be strings, ints, or floats
            })
            
            # Generate an ID since the dataset image doesn't show one
            ids.append(f"TKT-ITIL-{idx + 1000}")
            
    except FileNotFoundError:
        print(f"ERROR: Could not find '{dataset_filename}'. Please make sure it is in the same folder.")
        return
    except Exception as e:
        print(f"ERROR: {e}")
        return

    # 3. Batch insert into ChromaDB (Batching prevents crashing)
    batch_size = 100
    total_docs = len(documents)
    
    print(f"Found {total_docs} tickets. Starting embedding process...")

    for i in range(0, total_docs, batch_size):
        end_idx = min(i + batch_size, total_docs)
        print(f"Upserting batch {i} to {end_idx}...")
        collection.add(
            documents=documents[i:end_idx],
            metadatas=metadatas[i:end_idx],
            ids=ids[i:end_idx]
        )

    print("\n✅ SUCCESS! Enterprise ITIL Database populated.")
    print(f"Your RAG Node should now point to collection: '{collection_name}'")

if __name__ == "__main__":
    ingest_tickets()