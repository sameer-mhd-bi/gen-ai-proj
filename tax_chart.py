import pandas as pd
import plotly.express as px

# 1. Your 5-Level Deep Insurance Taxonomy Data
taxonomy_tree = {
    "Property Insurance": {
        "Commercial Property": {
            "Building Property Coverage": {
                "Windstorm Damage": ["Roof Structure Failure", "Broken Window Panes"],
                "Water Damage": ["Internal Pipe Burst", "External Flood Ingress"]
            },
            "Business Personal Property": {
                "Water Damage": ["Inventory Stock Spoilage", "Machinery Short-Circuit"],
                "Fire Damage": ["Smoke Discoloration", "Total Equipment Loss"]
            }
        }
    },
    "Casualty Insurance": {
        "Auto Liability": {
            "Bodily Injury Liability": {
                "Third Party Rear-End": ["Cervical Whiplash", "Soft Tissue Strain"],
                "Intersection Collision": ["Bone Fractures", "Concussion Trauma"]
            },
            "Property Damage Liability": {
                "Third Party Vehicle Damage": ["Rear Bumper Crushing", "Total Loss Structural Panel"]
            }
        },
        "Workers Compensation": {
            "Medical Only Benefits": {
                "Slip and Fall Injury": ["Ankle Fracture", "Wrist Sprain"],
                "Repetitive Motion Strain": ["Carpal Tunnel Syndrome", "Tendonitis Flareup"]
            },
            "Indemnity / Lost Wages": {
                "Industrial Machinery Accident": ["Amputation Rehabilitation", "Severe Laceration Recovery"]
            }
        }
    }
}

# 2. Flatten the nested dictionary into a tabular dataframe structure
rows = []
for l1, l2_dict in taxonomy_tree.items():
    for l2, l3_dict in l2_dict.items():
        for l3, l4_dict in l3_dict.items():
            for l4, l5_list in l4_dict.items():
                for l5 in l5_list:
                    rows.append({
                        "Root": "Insurance",
                        "L1: Line of Business": l1,
                        "L2: Product Subtype": l2,
                        "L3: Coverage Type": l3,
                        "L4: Peril Trigger": l4,
                        "L5: Granular Cause": l5,
                        "Value": 1  # Ensures uniform spacing for every leaf node
                    })

df = pd.DataFrame(rows)

# 3. Build the Sunburst Visualization
fig = px.sunburst(
    df,
    path=["Root", "L1: Line of Business", "L2: Product Subtype", "L3: Coverage Type", "L4: Peril Trigger", "L5: Granular Cause"],
    values="Value",
    title="Interactive 5-Level Insurance Taxonomy Explorer",
    color="L1: Line of Business",  # Distinct color theme for Property vs Casualty
    color_discrete_map={
        "Property Insurance": "#1f77b4",
        "Casualty Insurance": "#ff7f0e"
    })


# 4. Refine layout parameters for high readability
fig.update_traces(
    textinfo="label",
    insidetextorientation="radial"  # Curving the text naturally along the ring arcs
)
fig.update_layout(
    margin=dict(t=40, l=10, r=10, b=10),
    width=900,
    height=900
)

# 5. Display the interactive chart in browser or notebook
fig.show()
