import matplotlib.pyplot as plt
from transformers import pipeline

# 1. Initialize the Zero-Shot Classification Pipeline
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")


taxonomy_tree = {
    "Property Insurance": {
        "Commercial Property": {
            # Fixed: Split Building vs Personal Property at L3 to stop Water Damage overlap
            "Building Property Coverage": {
                "Windstorm Damage": ["Roof Structure Failure", "Broken Window Panes"],
                "Water Damage": ["Internal Pipe Burst", "External Flood Ingress"]
            },
            "Business Personal Property": {
                "Water Damage Contents": ["Inventory Stock Spoilage", "Machinery Short-Circuit"], # Unique name
                "Fire Damage": ["Smoke Discoloration", "Total Equipment Loss"]
            }
        }
    },
    "Casualty Insurance": {
        "Auto Liability": {
            "Bodily Injury Liability": {
                "Third Party Rear-End": ["Cervical Whiplash", "Soft Tissue Strain"],
                "Intersection Collision": ["Upper Extremity Fractures", "Concussion Trauma"] # Specific fracture type
            }
        },
        "Workers Compensation": {
            "Medical Only Benefits": {
                "Occupational Slip and Fall": ["Ankle Fracture", "Wrist Sprain"], # Clarified workplace context
                "Repetitive Motion Strain": ["Carpal Tunnel Syndrome", "Tendonitis Flareup"]
            },
            "Indemnity / Lost Wages": {
                "Industrial Machinery Accident": ["Amputation Rehabilitation", "Severe Laceration Recovery"]
            }
        },
        "General Liability": {
            # FIX L3: Change "Medical Payments" to an injury-focused phrase
            "Bodily Injury Coverage": {
                # FIX L4: Change "Premises Slip and Fall" to a broader, action-based phrase
                "Slip Trip or Fall Incident": ["Upper Extremity Fractures", "Soft Tissue Injury"]
            }
        }

    }
}

# 3. Target Unstructured Claims Data
raw_claims = [
"i was crossing road without noticing i fell down and my left hand got injured "
"doctor has adviced its fracture and have to undergo major operation to fix my broken hand bone"]

CONFIDENCE_THRESHOLD = 0.20  # 20% Safety Threshold
claim_labels = []
overall_scores = []

# Helper Function to Draw the Hierarchy Map Dynamically
def plot_claim_hierarchy(claim_num, text, path_labels, path_scores, final_score):
    plt.figure(figsize=(10, 5))

    # Define plot layers (X coordinates for levels)
    x_positions = [0, 1, 2, 3, 4, 5]
    y_position = 0

    # Node Names to display
    nodes = ["Insurance Root"] + path_labels
    scores_pct = [100.0] + [s * 100 for s in path_scores]

    # Draw branches (lines linking the nodes)
    for i in range(len(x_positions) - 1):
        plt.plot([x_positions[i], x_positions[i+1]], [y_position, y_position],
                 color='#bdc3c7', linestyle='-', linewidth=2, zorder=1)

    # Draw nodes dynamically
    for i, (node_name, score) in enumerate(zip(nodes, scores_pct)):
        # Color nodes dynamically: Blue for root, Green for high confidence, Red for warning
        if i == 0:
            node_color = '#2c3e50'
        elif score >= 70.0:
            node_color = '#27ae60'
        elif score >= 40.0:
            node_color = '#f39c12'
        else:
            node_color = '#c0392b'

        # Draw the node coordinate circle
        plt.scatter(x_positions[i], y_position, color=node_color, s=400, zorder=2)

        # Add classification labels on top of circles
        label_text = f"{node_name}\n({score:.1f}%)" if i > 0 else node_name
        plt.text(x_positions[i], y_position + 0.15, label_text,
                 ha='center', va='bottom', fontsize=9, fontweight='bold',
                 bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.3', edgecolor='#e2e8f0'))

    # Format the dynamic Matplotlib canvas wrapper
    plt.title(f"Visual Taxonomy Path for Claim #{claim_num}\nOverall Path Integrity: {final_score:.1f}%",
              fontsize=12, fontweight='bold', pad=20)
    plt.xlim(-0.5, 5.5)
    plt.ylim(-0.5, 0.8)
    plt.axis('off') # Clean look, remove background axes grid lines
    plt.tight_layout()

    # Save chart locally and clear memory
    plt.savefig(f"claim_{claim_num}_taxonomy_route.png", dpi=300)
    plt.show()
    plt.close()


print("==================================================================")
print("   AUTOMATED INSURANCE TAXONOMY CLASSIFICATION REPORT (WITH FIXED ROUTING)  ")
print("==================================================================\n")

for index, text in enumerate(raw_claims, 1):
    print(f"📄 CLAIM RECORD #{index}")
    print(f"Raw Input Text: \"{text}\"")
    print("-" * 66)

    # Arrays to gather analytical data purely for plotting purposes
    plot_labels = []
    plot_scores = []

    joint_probability = 1.0
    path_nodes = []

    # --- LEVEL 1 ---
    l1_candidates = list(taxonomy_tree.keys())
    res_l1 = classifier(text, candidate_labels=l1_candidates)
    top_l1, score_l1 = res_l1['labels'][0], res_l1['scores'][0]

    joint_probability *= score_l1
    path_nodes.append(f"[L1 Line of Biz]: {top_l1} ({score_l1:.1%})")
    plot_labels.append(top_l1)
    plot_scores.append(score_l1)

    # --- LEVEL 2 ---
    l2_candidates = list(taxonomy_tree[top_l1].keys())
    res_l2 = classifier(text, candidate_labels=l2_candidates)
    top_l2, score_l2 = res_l2['labels'][0], res_l2['scores'][0]

    joint_probability *= score_l2
    path_nodes.append(f"[L2 Product]: {top_l2} ({score_l2:.1%})")
    plot_labels.append(top_l2)
    plot_scores.append(score_l2)

    # --- LEVEL 3 ---
    l3_candidates = list(taxonomy_tree[top_l1][top_l2].keys())
    res_l3 = classifier(text, candidate_labels=l3_candidates)
    top_l3, score_l3 = res_l3['labels'][0], res_l3['scores'][0]

    joint_probability *= score_l3
    path_nodes.append(f"[L3 Coverage]: {top_l3} ({score_l3:.1%})")
    plot_labels.append(top_l3)
    plot_scores.append(score_l3)

    # --- LEVEL 4 (With Safety Guardrail) ---
    l4_candidates = list(taxonomy_tree[top_l1][top_l2][top_l3].keys())
    res_l4 = classifier(text, candidate_labels=l4_candidates)
    top_l4, score_l4 = res_l4['labels'][0], res_l4['scores'][0]

    # CRITICAL FIX: If the model's top choice is lower than 20%, evaluate alternate L3 branch if available
    if score_l4 < CONFIDENCE_THRESHOLD:
        alt_l3_candidates = [c for c in l3_candidates if c != top_l3]
        if alt_l3_candidates:
            # Backtrack to the next best Level 3 branch
            top_l3 = alt_l3_candidates[0]
            # Re-fetch new candidates for Level 4
            l4_candidates = list(taxonomy_tree[top_l1][top_l2][top_l3].keys())
            res_l4 = classifier(text, candidate_labels=l4_candidates)
            top_l4, score_l4 = res_l4['labels'][0], res_l4['scores'][0]

            # Recalculate the corrected values across parameters
            joint_probability = score_l1 * score_l2 * score_l3
            path_nodes[2] = f"[L3 Coverage (Backtracked)]: {top_l3}"
            plot_labels[2] = f"{top_l3}\n(Backtracked)"

    joint_probability *= score_l4
    path_nodes.append(f"[L4 Peril]: {top_l4} ({score_l4:.1%})")
    plot_labels.append(top_l4)
    plot_scores.append(score_l4)

    # --- LEVEL 5 ---
    l5_candidates = taxonomy_tree[top_l1][top_l2][top_l3][top_l4]
    res_l5 = classifier(text, candidate_labels=l5_candidates)
    top_l5, score_l5 = res_l5['labels'][0], res_l5['scores'][0]

    joint_probability *= score_l5
    path_nodes.append(f"[L5 Cause]: 🛑 {top_l5} ({score_l5:.1%})")
    plot_labels.append(top_l5)
    plot_scores.append(score_l5)

    overall_percentage = joint_probability * 100
    claim_labels.append(f"Claim #{index}")
    overall_scores.append(overall_percentage)

    # Output Fixed Visual Hierarchy to standard terminal shell
    print("[ROOT] Insurance")
    indent = " "
    for node in path_nodes:
        print(f"{indent}└── {node}")
        indent += "     "

    print(f"\n📊 SYSTEM PATH INTEGRITY SCORE: {overall_percentage:.1f}%")
    print("\n📈 Rendering path chart...")

    # Call the charting function inline inside loop execution context
    plot_claim_hierarchy(index, text, plot_labels, plot_scores, overall_percentage)

    print("\n" + "=" * 66 + "\n")
