import os
import random
import sys
from dotenv import load_dotenv
from faker import Faker
import psycopg2
from neo4j import GraphDatabase
from langchain_pinecone import PineconeVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pinecone import Pinecone
from app.core.llm_setup import get_embeddings

load_dotenv()
fake = Faker()

# ==========================================
# 1. SYNTHETIC DATA GENERATION ENGINE
# ==========================================
print("Generating Realistic Mock for Chromatic Prism Corp")

# Expanded Department, C-Suite, and Role Mapping
DEPT_STRUCTURE = {
    "Engineering": {"c_level": "CTO",
                    "roles": ["Backend Engineer", "Frontend Engineer", "DevOps Engineer", "QA Automation Engineer",
                              "Data Scientist"]},
    "Finance": {"c_level": "CFO",
                "roles": ["Financial Analyst", "Accountant", "Payroll Specialist", "Controller", "Tax Specialist"]},
    "Operations": {"c_level": "COO", "roles": ["Operations Analyst", "Logistics Coordinator", "Supply Chain Manager",
                                               "Facilities Manager"]},
    "Marketing": {"c_level": "CMO",
                  "roles": ["Content Strategist", "SEO Specialist", "Campaign Manager", "Graphic Designer",
                            "PR Specialist"]},
    "Sales": {"c_level": "CRO",
              "roles": ["Account Executive", "Sales Development Rep", "Sales Engineer", "Regional Account Manager"]},
    "HR": {"c_level": "CHRO", "roles": ["Technical Recruiter", "HR Business Partner", "Benefits Coordinator",
                                        "Diversity & Inclusion Specialist"]},
    "Product": {"c_level": "CPO",
                "roles": ["Product Manager", "UX Researcher", "UI Designer", "Scrum Master", "Technical Writer"]},
    "Legal": {"c_level": "CLO",
              "roles": ["Corporate Counsel", "Compliance Officer", "Paralegal", "Contracts Administrator"]},
    "IT": {"c_level": "CIO",
           "roles": ["Systems Administrator", "Helpdesk Technician", "Network Engineer", "Cybersecurity Analyst"]},
    "Customer Success": {"c_level": "CCO", "roles": ["Customer Success Manager", "Technical Support Specialist",
                                                     "Implementation Consultant"]}
}

PROJECT_ADJECTIVES = ["Quantum", "Neural", "Cyber", "Aero", "Hyper", "Crypto", "Nano", "Echo", "Solar", "Nova", "Citadel", "Vortex", "Zenith", "Pinnacle", "Vertex", "Stratus"]
PROJECT_NOUNS = ["Matrix", "Core", "Pulse", "Forge", "Sphere", "Weave", "Nexus", "Grid", "Vault", "Engine", "Warden", "Beacon", "Horizon", "Summit", "Catalyst", "Monolith"]

employees = []
projects = []
hierarchy = []  # Tuples of (employee_id, manager_id)
project_assignments = []  # Tuples of (employee_id, project_id, role)
used_project_names = set()

# 1a. Generate 15 Projects
for i in range(1, 16):
    while True:
        # Generate a candidate name from your custom lists
        adj = random.choice(PROJECT_ADJECTIVES)
        noun = random.choice(PROJECT_NOUNS)
        project_name = f"Project {adj} {noun}"

        # Check if we've used this exact name before
        if project_name not in used_project_names:
            used_project_names.add(project_name)
            projects.append({
                "id": f"P{i}",
                "name": project_name,
                "budget": random.randint(50, 100000) * 100000,
                "status": random.choice(["Active", "Completed", "Planning", "On Hold", "Cancelled"])
            })
            break  # Exit the while loop and move to the next project ID

# 1b. Generate Employees & 3-Tier Hierarchy (C-Suite -> Director -> Staff)
emp_id_counter = 1

# --- Tier 1: CEO ---
ceo = {"id": emp_id_counter, "name": fake.name(), "dept": "Executive", "salary": 650000, "role": "CEO"}
employees.append(ceo)
emp_id_counter += 1

c_suite_execs = {}  # Map dept name to executive employee object
directors = {}  # Map dept name to list of director employee objects

# --- Tier 2: C-Suite (1 per department) ---
for dept, data in DEPT_STRUCTURE.items():
    exec_emp = {
        "id": emp_id_counter,
        "name": fake.name(),
        "dept": dept,
        "salary": random.randint(250, 500) * 1000,
        "role": data["c_level"]
    }
    employees.append(exec_emp)
    hierarchy.append((exec_emp["id"], ceo["id"]))  # C-Suite reports to CEO
    c_suite_execs[dept] = exec_emp
    directors[dept] = []
    emp_id_counter += 1

# --- Tier 3: Directors (2 per department) ---
for dept in DEPT_STRUCTURE.keys():
    for _ in range(2):
        dir_emp = {
            "id": emp_id_counter,
            "name": fake.name(),
            "dept": dept,
            "salary": random.randint(160, 330) * 1000,
            "role": f"Director of {dept}"
        }
        employees.append(dir_emp)
        hierarchy.append((dir_emp["id"], c_suite_execs[dept]["id"]))  # Directors report to C-Suite
        directors[dept].append(dir_emp)
        emp_id_counter += 1

# --- Tier 4: Staff (120 employees distributed across departments) ---
for _ in range(120):
    dept = random.choice(list(DEPT_STRUCTURE.keys()))
    role = random.choice(DEPT_STRUCTURE[dept]["roles"])

    # Slight salary bands based on role type
    if "Engineer" in role or "Scientist" in role or "Specialist" in role or "Manager" in role:
        salary = random.randint(80, 210) * 1000
    else:
        salary = random.randint(50, 180) * 1000

    staff_emp = {
        "id": emp_id_counter,
        "name": fake.name(),
        "dept": dept,
        "salary": salary,
        "role": role
    }
    employees.append(staff_emp)

    # Assign staff to a random director within their department
    manager = random.choice(directors[dept])
    hierarchy.append((staff_emp["id"], manager["id"]))

    # Assign to 1-2 random projects
    for _ in range(random.randint(1, 2)):
        proj = random.choice(projects)
        project_assignments.append((staff_emp["id"], proj["id"], "Contributor"))

    emp_id_counter += 1

# Assign Directors to lead projects
for dir_list in directors.values():
    for director in dir_list:
        proj = random.choice(projects)
        project_assignments.append((director["id"], proj["id"], "Lead"))


# ==========================================
# 2. Relational DB Ingestion (Neon Postgres)
# ==========================================
def ingest_sql_data():
    print(f"\nStarting SQL Ingestion ({len(employees)} Employees, {len(DEPT_STRUCTURE) + 1} Departments)")
    db_url = os.getenv("MASTER_DATABASE_URL")
    if not db_url: return print("Skipping SQL: DATABASE_URL not found.")

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        cursor.execute("DROP TABLE IF EXISTS employees CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS departments CASCADE;")

        cursor.execute("""
                       CREATE TABLE departments
                       (
                           name             VARCHAR(50) PRIMARY KEY,
                           operating_budget INT
                       );
                       """)
        cursor.execute("""
                       CREATE TABLE employees
                       (
                           id         INT PRIMARY KEY,
                           name       VARCHAR(100),
                           department VARCHAR(50) REFERENCES departments (name),
                           salary     INT,
                           role       VARCHAR(100)
                       );
                       """)

        # Insert Departments (Including Executive)
        cursor.execute("INSERT INTO departments (name, operating_budget) VALUES ('Executive', 50000000);")
        for dept in DEPT_STRUCTURE.keys():
            cursor.execute("INSERT INTO departments (name, operating_budget) VALUES (%s, %s);",
                           (dept, random.randint(2000000, 35000000)))

        # Insert Employees
        for emp in employees:
            cursor.execute(
                "INSERT INTO employees (id, name, department, salary, role) VALUES (%s, %s, %s, %s, %s);",
                (emp["id"], emp["name"], emp["dept"], emp["salary"], emp["role"])
            )

        conn.commit()
        cursor.close()
        conn.close()
        print("SQL Ingestion Complete!")
    except Exception as e:
        print(f"SQL Error: {e}")


# ==========================================
# 3. Graph DB Ingestion (Neo4j Aura)
# ==========================================
def ingest_graph_data():
    num_hierarchy = len(hierarchy)
    num_assignments = len(project_assignments)
    total_rels = num_hierarchy + num_assignments
    print(f"\nStarting Graph Ingestion ({total_rels} Relationships, {num_assignments} Project Nodes, {num_hierarchy} Direct Reports")
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    pwd = os.getenv("NEO4J_PASSWORD")

    if not uri or not pwd: return print("Skipping Graph: Neo4j credentials not found.")

    try:
        driver = GraphDatabase.driver(uri, auth=(user, pwd))
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n;")

            # Insert Employees
            for emp in employees:
                session.run("CREATE (e:Employee {id: $id, name: $name, role: $role, dept: $dept})", **emp)

            # Insert Projects
            for proj in projects:
                session.run("CREATE (p:Project {id: $id, name: $name, status: $status})", **proj)

            # Insert Reporting Hierarchy
            for emp_id, mgr_id in hierarchy:
                session.run("""
                    MATCH (emp:Employee {id: $emp_id})
                    MATCH (mgr:Employee {id: $mgr_id})
                    CREATE (emp)-[:REPORTS_TO]->(mgr)
                """, emp_id=emp_id, mgr_id=mgr_id)

            # Insert Project Assignments
            for emp_id, proj_id, role in project_assignments:
                rel_type = "LEADS" if role == "Lead" else "CONTRIBUTES_TO"
                session.run(f"""
                    MATCH (emp:Employee {{id: $emp_id}})
                    MATCH (proj:Project {{id: $proj_id}})
                    CREATE (emp)-[:{rel_type}]->(proj)
                """, emp_id=emp_id, proj_id=proj_id)

        driver.close()
        print("Graph Ingestion Complete!")
    except Exception as e:
        print(f"Graph Error: {e}")


# ==========================================
# 4. Vector DB Ingestion (Pinecone)
# ==========================================
def ingest_vector_data():
    print(f"\nStarting Vector Ingestion (Elaborate Dynamic Wiki & Policy Documents)")
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if not api_key or not gemini_key: return print("Skipping Vector: Pinecone or Gemini API keys missing.")

    try:
        pc = Pinecone(api_key=api_key)
        index = pc.Index(index_name)
        index.delete(delete_all=True)
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2-preview", google_api_key=gemini_key)
        docs = []

        # 1. EXPANDED PROJECT WIKIS (More detailed milestones and tech stacks)
        for proj in projects:
            assigned_emps = [e for e, p, r in project_assignments if p == proj["id"]]
            emp_names = [emp["name"] for emp in employees if emp["id"] in assigned_emps]
            lead_emps = [emp["name"] for emp in employees if
                         emp["id"] in [e for e, p, r in project_assignments if p == proj["id"] and r == "Lead"]]

            lead_str = f"Led by {', '.join(lead_emps)}, " if lead_emps else "Currently seeking a dedicated Lead, "

            content = f"CONFIDENTIAL INTERNAL WIKI - DOCUMENT REF: {proj['id']} - {proj['name']}. \n"
            content += f"PHASE & BUDGET: This initiative is actively tracked in the '{proj['status']}' lifecycle phase. Finance has authorized an operational budget of ₹{proj['budget']:,.2f} for Q3/Q4. "
            content += f"Overage requests exceeding 10% must be flagged to the CFO, {c_suite_execs['Finance']['name']}.\n"
            content += f"TEAM COMPOSITION: {lead_str}the core delivery matrix includes the following personnel: {', '.join(emp_names)}. "
            content += f"Contractors scaling this team must complete NDA onboarding.\n"
            content += f"TECHNICAL SCOPE: The primary objective of {proj['name']} is to architect a highly available {fake.bs()} system. "
            content += f"We are utilizing a microservices architecture deployed via Kubernetes. All database schemas require review by the Lead Data Scientist before production commits. "
            content += f"Compliance sign-off is strictly enforced and must be routed through the Legal desk, specifically overseen by {c_suite_execs['Legal']['name']} ({c_suite_execs['Legal']['role']}) to ensure GDPR alignment."

            docs.append(Document(page_content=content, metadata={"source": "Project_Wiki", "project_id": proj["id"]}))

        # 2. ELABORATE HR & WORKPLACE POLICIES
        docs.append(Document(
            page_content=f"REMOTE WORK & TELECOMMUTING POLICY (V2.4): \nScope: Applies to all full-time and part-time staff of Chromatic Prism Corp.\nGuidelines: Employees reporting directly to the CEO, {ceo['name']}, or any C-level executive (e.g., {c_suite_execs['Engineering']['name']}, the {c_suite_execs['Engineering']['role']}) are classified as 'Hybrid-Essential' and must be present at the corporate headquarters a minimum of 4 days per week (Monday-Thursday). \nStaff operating under the Director level are granted 'Flexible Remote' status. \nExceptions: Medical exceptions or permanent relocations must be documented and countersigned by the CHRO, {c_suite_execs['HR']['name']}. \nStipend: Fully remote employees are eligible for a one-time ₹15000 home office provisioning stipend upon their 90-day anniversary.",
            metadata={"source": "HR_Policy", "category": "Remote Work"}
        ))

        docs.append(Document(
            page_content=f"PAID TIME OFF (PTO), LEAVE, & SABBATICAL: \nStructure: Chromatic Prism Corp utilizes an 'Unlimited/Discretionary PTO' model for salaried exempt employees. \nApproval Matrix: Continuous leave of 1 to 4 days requires standard Manager approval. Leave spanning 5 to 14 continuous business days requires a 30-day advance notice and formal approval from your department Director. \nSabbatical: Employees achieving 5 continuous years of service are eligible for a 6-week fully paid sabbatical. \nParental Leave: Primary caregivers receive 16 weeks of fully paid leave; secondary caregivers receive 8 weeks. \nAdministration: All medical, FMLA, and parental leave cases bypass the standard hierarchy and are strictly managed by the HR Benefits Portal under the authority of {c_suite_execs['HR']['name']}.",
            metadata={"source": "HR_Policy", "category": "Time Off"}
        ))

        docs.append(Document(
            page_content=f"PERFORMANCE REVIEW & PROMOTION CYCLE: \nCadence: Chromatic Prism Corp executes formal performance evaluations bi-annually (May and November). \nStructure: The review consists of a self-evaluation, peer 360-feedback, and a Manager calibration. \nPerformance Improvement Plans (PIP): Employees failing to meet KPI targets for two consecutive quarters will be placed on a 60-day PIP. PIP templates must be drafted in coordination with the HR Business Partner. \nPromotions: Out-of-cycle promotions are strictly prohibited unless authorized by the department's C-level executive and the CFO, {c_suite_execs['Finance']['name']}, to ensure salary band compliance.",
            metadata={"source": "HR_Policy", "category": "Performance"}
        ))

        docs.append(Document(
            page_content=f"CODE OF CONDUCT, ETHICS, & WHISTLEBLOWER POLICY: \nZero Tolerance: Chromatic Prism Corp maintains a strict zero-tolerance policy regarding workplace harassment, discrimination, insider trading, and retaliation. \nReporting Hierarchy: Violations should be immediately reported to your direct Director. \nWhistleblower Exception: If the offending party is your Director or higher, the report must bypass the standard chain of command. \nEthics Hotline: Anonymous reports can be submitted via the 24/7 Ethics Portal, which is maintained by an external third party and audited directly by the Operations department, overseen by {c_suite_execs['Operations']['name']} ({c_suite_execs['Operations']['role']}).",
            metadata={"source": "HR_Policy", "category": "Ethics"}
        ))

        # 3. ELABORATE IT, SECURITY & ENGINEERING POLICIES
        docs.append(Document(
            page_content=f"IT HARDWARE PROVISIONING & ASSET LIFECYCLE: \nStandard Issue: New engineering hires are provisioned with an Apple MacBook Pro M3 Max or equivalent Linux workstation. Non-engineering staff are provisioned with standard ultrabooks. \nCustom Requests: Requests for specialized hardware, multi-GPU compute rigs, or testing devices must be logged via the IT Service Desk. \nFinancial Thresholds: Hardware requests exceeding a cost basis of ₹5,00,000 require secondary capital expenditure (CapEx) approval from the CFO, {c_suite_execs['Finance']['name']}. \nEnd of Life: Laptops are refreshed every 36 months. Old assets must be returned to IT for secure wiping and e-waste recycling.",
            metadata={"source": "IT_Policy", "category": "Hardware"}
        ))

        docs.append(Document(
            page_content=f"INFORMATION SECURITY (INFOSEC) & ACCESS CONTROL: \nEndpoint Security: All employee endpoints accessing the Chromatic Prism Corp VPN must run the mandatory CrowdStrike Falcon agent and our proprietary Mobile Device Management (MDM) profile. \nAuthentication: Passwords must be a minimum of 16 characters, utilize mixed casing/symbols, and be rotated every 90 days. YubiKey hardware MFA is required for all AWS and Production Database access. \nIncident Reporting: Lost or stolen devices must be reported to the Helpdesk within 2 hours of discovery. \nEscalation: Severe data breaches or ransomware indicators trigger a SEV-1 alert, immediately escalating to {c_suite_execs['IT']['name']}, the {c_suite_execs['IT']['role']}, and the corporate legal team.",
            metadata={"source": "IT_Policy", "category": "Security"}
        ))

        docs.append(Document(
            page_content=f"INCIDENT RESPONSE (IR) & SEVERITY CLASSIFICATION: \nDefinitions: \nSEV-1 (Critical): Total system outage or active data breach. All hands required. \nSEV-2 (High): Core feature broken for >10% of customers. \nSEV-3 (Medium): Degradation of non-critical services. \nProcedures: For SEV-1 and SEV-2 incidents, a temporary 'War Room' channel is created. An Incident Commander (IC) is appointed to direct engineering traffic. \nPost-Mortem: Within 48 hours of incident resolution, a blameless root-cause analysis (RCA) document must be published to the Engineering Wiki. The CTO, {c_suite_execs['Engineering']['name']}, reviews all SEV-1 post-mortems.",
            metadata={"source": "Engineering_Policy", "category": "Incident Response"}
        ))

        docs.append(Document(
            page_content=f"OPEN SOURCE SOFTWARE (OSS) INTEGRATION & LICENSING: \nApproved Licenses: Engineering teams may freely integrate third-party libraries licensed under MIT, Apache 2.0, or BSD. \nRestricted Licenses: Code operating under GPL (General Public License), AGPL, or any viral 'copyleft' license cannot be integrated into proprietary Chromatic Prism Corp codebases under any circumstances. \nApproval Process: Exceptions to the GPL restriction require an architecture review and explicit, documented clearance from the Legal department, signed by {c_suite_execs['Legal']['name']} ({c_suite_execs['Legal']['role']}). Failure to comply may result in termination.",
            metadata={"source": "Engineering_Policy", "category": "Licensing"}
        ))

        # 4. ELABORATE FINANCE, LEGAL & COMPLIANCE POLICIES
        docs.append(Document(
            page_content=f"CORPORATE TRAVEL & EXPENSE REIMBURSEMENT (T&E): \nAir Travel: Domestic flights must be booked Economy class. International flights exceeding 8 continuous hours of airtime may be booked in Premium Economy or Business Class with VP approval. \nPer Diem: Meal expenses are capped at ₹7500/day for domestic travel and ₹18000/day for international travel. Alcohol is not reimbursable unless entertaining external clients. \nSoftware Subscriptions: Unauthorized 'shadow IT' SaaS subscriptions over ₹5000/month must be pre-approved by IT and Finance. \nAuditing: Expense reports must be submitted via Confluence within 30 days. Expense anomalies and continuous violations are subject to quarterly audit by {c_suite_execs['Finance']['name']} ({c_suite_execs['Finance']['role']}).",
            metadata={"source": "Finance_Policy", "category": "Expenses"}
        ))

        docs.append(Document(
            page_content=f"VENDOR PROCUREMENT & CONTRACTING: \nThresholds: Purchases or software contracts under ₹10,00,000 can be approved by Department Directors. Contracts spanning ₹10,00,001 to ₹1,00,00,000 require C-Level sign-off. Contracts exceeding ₹1,00,00,000 require a formal Request for Proposal (RFP) process with at least 3 competing vendor bids. \nLegal Review: All vendor Master Services Agreements (MSAs) and Non-Disclosure Agreements (NDAs) must be redlined and approved by Corporate Counsel, overseen by {c_suite_execs['Legal']['name']}. \nPayment Terms: Standard corporate payment terms are Net-60.",
            metadata={"source": "Finance_Policy", "category": "Procurement"}
        ))

        docs.append(Document(
            page_content=f"DATA PRIVACY & PII HANDLING (GDPR/CCPA COMPLIANCE): \nScope: This directive dictates the handling of Personally Identifiable Information (PII) of Chromatic Prism Corp's users. \nStorage Requirements: All PII must be encrypted at rest using AES-256 and in transit via TLS 1.3. \nData Retention: User analytics data is retained for 24 months before anonymization. Billing records are kept for 7 years to comply with tax laws. \nRight to be Forgotten: Customer requests for data deletion must be executed within 14 business days across all primary and backup databases. \nCompliance Officer: The execution of our privacy framework falls under the mandate of the CLO, {c_suite_execs['Legal']['name']}.",
            metadata={"source": "Legal_Policy", "category": "Privacy"}
        ))

        # 5. ELABORATE BRANDING & COMMUNICATIONS
        secret_project = random.choice([p for p in projects if p["status"] == "Active"])

        docs.append(Document(
            page_content=f"PUBLIC RELATIONS, SOCIAL MEDIA & MEDIA INQUIRIES: \nSpokespersons: Only designated members of the Marketing and Executive teams are authorized to speak to the press on behalf of Chromatic Prism Corp. \nInquiries: All unprompted media requests must be forwarded immediately to the CMO, {c_suite_execs['Marketing']['name']}. \nSocial Media: Employees are encouraged to share published company news. However, staff are strictly prohibited from leaking or discussing unannounced internal initiatives, roadmaps, or beta programs (specifically including confidential efforts like {secret_project['name']}) on personal social media platforms like X, LinkedIn, or Reddit.",
            metadata={"source": "Marketing_Policy", "category": "Communications"}
        ))

        docs.append(Document(
            page_content=f"BRAND ASSET GUIDELINES: \nLogo Usage: The Chromatic Prism Corp primary logo must maintain a minimum clear space equal to 50% of the logo's height. The logo must never be stretched, recolored, or placed on a heavily patterned background. \nTypography: The official corporate typefaces are 'Inter' for digital interfaces and web copy, and 'Merriweather' for printed collateral and formal letterheads. \nApproval: External marketing materials, pitch decks, and conference booth designs must be reviewed for brand consistency by the Marketing department, led by {c_suite_execs['Marketing']['name']}.",
            metadata={"source": "Marketing_Policy", "category": "Branding"}
        ))

        # Initialize the vector store connection first
        vectorstore = PineconeVectorStore(index_name=index_name, embedding=embeddings, pinecone_api_key=api_key)

        # Add documents one at a time
        for i, doc in enumerate(docs):
            vectorstore.add_documents([doc])
            print(
                f"Uploaded {i + 1}/{len(docs)}: {doc.metadata.get('source')} - {doc.metadata.get('category', 'Project')}")

        print(f"Vector Ingestion Complete! Successfully embedded and uploaded all {len(docs)} documents.")
    except Exception as e:
        print(f"Vector Error: {e}")


if __name__ == "__main__":
    print("Starting Scaled Chromatic Prism Corp Data Initialization")
    ingest_sql_data()
    ingest_graph_data()
    ingest_vector_data()
    print("\nInitialization Finished")