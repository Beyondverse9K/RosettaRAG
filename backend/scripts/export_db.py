import os
import csv
import json
import psycopg2
from neo4j import GraphDatabase
from pinecone import Pinecone
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Create a backups directory if it doesn't exist
BACKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


# 1. Export Relational DB (Neon Postgres) to CSV

def export_sql_to_csv():
    print("Starting SQL Export...")
    db_url = os.getenv("MASTER_DATABASE_URL")
    if not db_url: return print("Skipping SQL: DATABASE_URL not found.")

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        tables = ['departments', 'employees']

        for table in tables:
            cursor.execute(f"SELECT * FROM {table};")
            rows = cursor.fetchall()

            # Get column names
            colnames = [desc[0] for desc in cursor.description]

            filepath = os.path.join(BACKUP_DIR, f"{table}_backup_{timestamp}.csv")
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(colnames)  # Write headers
                writer.writerows(rows)  # Write data

            print(f"Exported {len(rows)} rows to {filepath}")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"SQL Export Error: {e}")


# 2. Export Graph DB (Neo4j Aura) to JSON

def export_graph_to_json():
    print("\nStarting Graph Export...")
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    pwd = os.getenv("NEO4J_PASSWORD")

    if not uri or not pwd: return print("Skipping Graph: Neo4j credentials not found.")

    try:
        driver = GraphDatabase.driver(uri, auth=(user, pwd))
        nodes_data = []
        rels_data = []

        with driver.session() as session:
            # Export Nodes
            nodes_result = session.run("MATCH (n) RETURN labels(n) AS labels, properties(n) AS properties")
            for record in nodes_result:
                nodes_data.append({
                    "labels": record["labels"],
                    "properties": record["properties"]
                })

            # Export Relationships
            rels_result = session.run(
                "MATCH (a)-[r]->(b) RETURN properties(a).id AS source_id, type(r) AS rel_type, properties(b).id AS target_id")
            for record in rels_result:
                rels_data.append({
                    "source_id": record["source_id"],
                    "relationship": record["rel_type"],
                    "target_id": record["target_id"]
                })

        # Save to JSON
        graph_backup = {"nodes": nodes_data, "relationships": rels_data}
        filepath = os.path.join(BACKUP_DIR, f"graph_backup_{timestamp}.json")

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(graph_backup, f, indent=4)

        print(f"Exported Graph Data to {filepath}")
        driver.close()
    except Exception as e:
        print(f"Graph Export Error: {e}")


# 3. Export Vector DB (Pinecone) to JSON

def export_pinecone_to_json():
    print("\nStarting Vector Export...")
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME", "enterprise-rag-index")

    if not api_key:
        return print("Skipping Vector: PINECONE_API_KEY not found.")

    try:
        pc = Pinecone(api_key=api_key)
        index = pc.Index(index_name)

        all_vectors = []

        # Pinecone's list() method acts as a generator that handles pagination automatically.
        # It yields batches of vector IDs.
        print("Fetching vector IDs from Pinecone")
        for ids_batch in index.list():
            if not ids_batch:
                continue

            # Once we have a batch of IDs, we use fetch() to grab the actual numerical values and text metadata
            fetch_response = index.fetch(ids=ids_batch)

            # Use dot notation for Pinecone V3+ objects
            if hasattr(fetch_response, 'vectors'):
                for vector_id, vector_data in fetch_response.vectors.items():
                    all_vectors.append({
                        "id": vector_id,
                        "values": vector_data.values,
                        "metadata": vector_data.metadata
                    })

        # Save to JSON
        filepath = os.path.join(BACKUP_DIR, f"pinecone_backup_{timestamp}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(all_vectors, f, indent=4)

        print(f"Exported {len(all_vectors)} vectors (and their metadata) to {filepath}")

    except Exception as e:
        print(f"Vector Export Error: {e}")

if __name__ == "__main__":
    print("Starting Local Backup")
    export_sql_to_csv()
    export_graph_to_json()
    export_pinecone_to_json()
    print("\nBackup Finished")