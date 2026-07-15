import os
import json
import psycopg2
from sentence_transformers import SentenceTransformer

def main():
    print("Starting database initialization...")
    
    # 1. Connect to PostgreSQL
    params = {"dbname": "insurance_db", "user": "postgres", "password": "root", "host": "localhost", "port": "5432"}
    try:
        conn = psycopg2.connect(**params)
        conn.autocommit = True
        cursor = conn.cursor()
        print("Connected to PostgreSQL successfully.")
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return

    # 2. Recreate schema
    print("Recreating database tables...")
    cursor.execute("""
        DROP TABLE IF EXISTS claims CASCADE;
        DROP TABLE IF EXISTS policies CASCADE;
        DROP TABLE IF EXISTS customers CASCADE;
    """)
    
    cursor.execute("""
        CREATE TABLE customers (
            id SERIAL PRIMARY KEY,
            customer_id VARCHAR(50) UNIQUE NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            email VARCHAR(100),
            phone VARCHAR(50),
            address TEXT
        );
    """)
    
    cursor.execute("""
        CREATE TABLE policies (
            id SERIAL PRIMARY KEY,
            policy_number VARCHAR(50) UNIQUE NOT NULL,
            customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
            policy_type VARCHAR(50) NOT NULL,
            coverage_details TEXT
        );
    """)
    
    cursor.execute("""
        CREATE TABLE claims (
            id SERIAL PRIMARY KEY,
            claim_id VARCHAR(50) UNIQUE NOT NULL,
            policy_id INTEGER REFERENCES policies(id) ON DELETE CASCADE,
            description TEXT NOT NULL,
            peril VARCHAR(100),
            damage_type VARCHAR(100),
            structure VARCHAR(100),
            estimated_loss NUMERIC(12, 2),
            status VARCHAR(50) DEFAULT 'Pending',
            recommendation VARCHAR(50),
            embedding REAL[]
        );
    """)
    print("Tables created successfully.")

    # 3. Load Customers
    script_dir = os.path.dirname(os.path.abspath(__file__))
    customers_file = os.path.join(script_dir, "..", "dummy_customers.json")
    
    if os.path.exists(customers_file):
        print(f"Loading customers from {customers_file}...")
        with open(customers_file, "r", encoding="utf-8") as f:
            dummy_customers = json.load(f)
    else:
        print("Warning: dummy_customers.json not found, using default list.")
        dummy_customers = [
            {"customer_id": "CUST_001", "full_name": "James Sterling", "email": "j.sterling@mailnet.com", "phone": "+91 98765 43210", "address": "42, Green Glen Layout, Bellandur, Bengaluru"},
            {"customer_id": "CUST_002", "full_name": "Anita Rao", "email": "anita.r.1990@webmail.in", "phone": "+91 91234 56789", "address": "15, Park Street, Sector 2, Salt Lake, Kolkata"},
            {"customer_id": "CUST_003", "full_name": "Jamie Sterling", "email": "admin@opssecure.net", "phone": "+91 98765 43211", "address": "42, Green Glen Layout, Bellandur, Bengaluru"},
            {"customer_id": "CUST_004", "full_name": "Vikram Malhotra", "email": "v.malhotra@mailnet.com", "phone": "+91 88888 77777", "address": "78, Phase 3, Hitech City, Hyderabad"},
            {"customer_id": "CUST_005", "full_name": "Siddharth Shah", "email": "admin@opssecure.net", "phone": "+91 77777 66666", "address": "Suite 401, Tech Park Towers, Whitefield, Bengaluru"}
        ]

    # Insert Customers and save DB IDs mapped by customer_id string
    customer_db_ids = {}
    for cust in dummy_customers:
        cursor.execute("""
            INSERT INTO customers (customer_id, full_name, email, phone, address)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """, (cust["customer_id"], cust["full_name"], cust.get("email"), cust.get("phone"), cust.get("address")))
        customer_db_ids[cust["customer_id"]] = cursor.fetchone()[0]
    
    print(f"Inserted {len(customer_db_ids)} customers.")

    # 4. Insert Policies
    policies_data = [
        {"policy_number": "POL-991823", "customer_id": "CUST_001", "policy_type": "Commercial Property", "coverage_details": "Covers building structures, roofing, and window damage due to weather."},
        {"policy_number": "POL-445122", "customer_id": "CUST_002", "policy_type": "Workers Comp", "coverage_details": "Covers medical expenses and recovery for workplace accidental injuries."},
        {"policy_number": "POL-CAR-445122", "customer_id": "CUST_002", "policy_type": "Car Insurance", "coverage_details": "Covers vehicle damage, collision costs, third-party auto liability, and comprehensive auto risks."},
        {"policy_number": "POL-991824", "customer_id": "CUST_003", "policy_type": "Commercial Auto", "coverage_details": "Covers third-party liability, vehicle crashes, and collision damage."},
        {"policy_number": "POL-112233", "customer_id": "CUST_004", "policy_type": "General Liability", "coverage_details": "Covers bodily injury and slip & fall medical payments on premises."},
        {"policy_number": "POL-556677", "customer_id": "CUST_005", "policy_type": "Homeowners B", "coverage_details": "Covers detached structures, workshop buildings, and wind damage."}
    ]
    
    policy_db_ids = {}
    for pol in policies_data:
        cust_db_id = customer_db_ids.get(pol["customer_id"])
        if not cust_db_id:
            continue
        cursor.execute("""
            INSERT INTO policies (policy_number, customer_id, policy_type, coverage_details)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """, (pol["policy_number"], cust_db_id, pol["policy_type"], pol["coverage_details"]))
        policy_db_ids[pol["policy_number"]] = cursor.fetchone()[0]

    print(f"Inserted {len(policy_db_ids)} policies.")

    # 5. Define Claims (based on sample.txt descriptions)
    claims_data = [
        {
            "claim_id": "CLM-90214",
            "policy_number": "POL-991823",
            "description": "High winds during the storm yesterday blew several shingles off the roof, causing severe structural failure and broken window panes in our main warehouse.",
            "peril": "Windstorm",
            "damage_type": "Fallen Shingles",
            "structure": "Main Warehouse",
            "estimated_loss": 12000.00,
            "status": "Approved",
            "recommendation": "Approve"
        },
        {
            "claim_id": "CLM-80122",
            "policy_number": "POL-445122",
            "description": "While crossing the factory floor, an employee slipped on a wet surface and fell, resulting in a fractured ankle and a severely sprained wrist.",
            "peril": "Slip and Fall",
            "damage_type": "Fractured Ankle / Sprained Wrist",
            "structure": "Factory Floor",
            "estimated_loss": 4500.00,
            "status": "Approved",
            "recommendation": "Approve"
        },
        {
            "claim_id": "CLM-77543",
            "policy_number": "POL-991824",
            "description": "Our delivery truck failed to brake in time at the stoplight and hit the sedan in front of it. The driver of the sedan is claiming a severe cervical whiplash and soft tissue strain in their neck.",
            "peril": "Auto Collision",
            "damage_type": "Cervical Whiplash",
            "structure": "Delivery Truck / Third-Party Sedan",
            "estimated_loss": 8500.00,
            "status": "Approved",
            "recommendation": "Approve"
        },
        {
            "claim_id": "CLM-70118",
            "policy_number": "POL-991824",
            "description": "A driver ran a red light at the intersection and collided with our insured's vehicle. The passenger sustained upper extremity fractures and a severe concussion trauma from the impact.",
            "peril": "Auto Collision",
            "damage_type": "Concussion / Fractures",
            "structure": "Insured Vehicle",
            "estimated_loss": 15000.00,
            "status": "Manual Review",
            "recommendation": "Manual Review"
        },
        {
            "claim_id": "CLM-61192",
            "policy_number": "POL-112233",
            "description": "A customer was walking through the grocery aisle, slipped on an unmarked puddle of spilled liquid, and suffered upper extremity fractures along with a soft tissue injury to their shoulder.",
            "peril": "Slip and Fall",
            "damage_type": "Upper Extremity Fractures",
            "structure": "Grocery Aisle",
            "estimated_loss": 9500.00,
            "status": "Approved",
            "recommendation": "Approve"
        },
        {
            "claim_id": "CLM-55210",
            "policy_number": "POL-991823",
            "description": "During the freezing temperatures last night, an internal pipe burst on the second floor. The external flood ingress ruined the carpeting and drywall on the entire first level.",
            "peril": "Water Damage",
            "damage_type": "Internal Pipe Burst",
            "structure": "Office Building",
            "estimated_loss": 22000.00,
            "status": "Approved",
            "recommendation": "Approve"
        },
        {
            "claim_id": "CLM-44381",
            "policy_number": "POL-991823",
            "description": "An electrical fire broke out in the server room, resulting in total equipment loss of our main servers and severe smoke discoloration to the surrounding inventory.",
            "peril": "Fire Damage",
            "damage_type": "Electrical Fire / Smoke Damage",
            "structure": "Server Room",
            "estimated_loss": 85000.00,
            "status": "Approved",
            "recommendation": "Approve"
        },
        {
            "claim_id": "CLM-33019",
            "policy_number": "POL-445122",
            "description": "The factory worker's hand got caught in the conveyor belt gears, resulting in an industrial machinery accident that required amputation rehabilitation and severe laceration recovery.",
            "peril": "Industrial Machinery Accident",
            "damage_type": "Laceration / Amputation",
            "structure": "Conveyor Belt Gears",
            "estimated_loss": 45000.00,
            "status": "Rejected",
            "recommendation": "Reject"
        },
        {
            "claim_id": "CLM-22104",
            "policy_number": "POL-445122",
            "description": "Our warehouse employee tripped over a pallet jack left in the aisle. The fall caused a fractured ankle and a torn ACL. Medical treatment is focused solely on the physical injury, with no lost wages claimed.",
            "peril": "Slip and Fall",
            "damage_type": "Fractured Ankle / ACL Tear",
            "structure": "Warehouse Aisle",
            "estimated_loss": 7500.00,
            "status": "Approved",
            "recommendation": "Approve"
        },
        {
            "claim_id": "CLM-11928",
            "policy_number": "POL-991824",
            "description": "A driver in our fleet swerved to avoid an animal and scraped the side of a parked SUV. There were no injuries, but the third-party vehicle sustained significant rear bumper crushing and structural panel damage.",
            "peril": "Auto Collision",
            "damage_type": "Bumper Crushing / Panel Damage",
            "structure": "Fleet Van / Parked SUV",
            "estimated_loss": 3200.00,
            "status": "Approved",
            "recommendation": "Approve"
        },
        {
            "claim_id": "CLM-11234",
            "policy_number": "POL-112233",
            "description": "A patron was exiting the building after hours when they slipped on the icy sidewalk and broke their arm. The resulting medical expenses are high, but it is a straightforward physical injury claim.",
            "peril": "Slip and Fall",
            "damage_type": "Broken Arm",
            "structure": "Icy Sidewalk",
            "estimated_loss": 6200.00,
            "status": "Approved",
            "recommendation": "Approve"
        },
        {
            "claim_id": "CLM-99882",
            "policy_number": "POL-991823",
            "description": "Heavy rain caused external flood ingress through a foundation crack. The water ruined the inventory stock of shoes and electronic goods stored on the ground floor, but no structural damage to the building itself occurred.",
            "peril": "Water Damage",
            "damage_type": "Inventory Spoilage / Flood Ingress",
            "structure": "Ground Floor Warehouse",
            "estimated_loss": 18500.00,
            "status": "Manual Review",
            "recommendation": "Manual Review"
        },
        {
            "claim_id": "CLM-88192",
            "policy_number": "POL-556677",
            "description": "High winds caused an old oak tree to snap and fall onto my detached workshop. The roof is destroyed and water entered the building causing $15,000 in damage.",
            "peril": "Windstorm",
            "damage_type": "Fallen Tree",
            "structure": "Detached Workshop",
            "estimated_loss": 15000.00,
            "status": "Approved",
            "recommendation": "Approve"
        }
    ]

    # 6. Load SentenceTransformer model to generate embeddings
    print("Loading SentenceTransformer model ('all-MiniLM-L6-v2')...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # 7. Generate embeddings and insert claims
    print("Generating embeddings and inserting claims...")
    for claim in claims_data:
        pol_db_id = policy_db_ids.get(claim["policy_number"])
        if not pol_db_id:
            continue
            
        # Vectorize description
        embedding = model.encode(claim["description"]).tolist()
        
        cursor.execute("""
            INSERT INTO claims (claim_id, policy_id, description, peril, damage_type, structure, estimated_loss, status, recommendation, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, (
            claim["claim_id"],
            pol_db_id,
            claim["description"],
            claim["peril"],
            claim["damage_type"],
            claim["structure"],
            claim["estimated_loss"],
            claim["status"],
            claim["recommendation"],
            embedding
        ))
        
    print(f"Successfully inserted {len(claims_data)} claims into database.")
    
    cursor.close()
    conn.close()
    print("Database initialization complete!")

if __name__ == "__main__":
    main()
