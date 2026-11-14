"""Generate the dedicated Bonus Multimodal Benchmark (`data/bonus/questions.json`) per ADVANCED.md.

Split & Category Requirements (locked BEFORE running experiments):
  - `dev` split (18 questions):
      * 15 answerable covering all 5 categories:
          - 3 `table`         (bd_q01 .. bd_q03)
          - 3 `image_diagram` (bd_q04 .. bd_q06)
          - 3 `chart`         (bd_q07 .. bd_q09)
          - 3 `multi_hop`     (bd_q10 .. bd_q12)
          - 3 `text`          (bd_q13 .. bd_q15)
      * 3 `unanswerable`      (bd_u01 .. bd_u03)
  - `test` split (30 questions):
      * 24 answerable strictly primary-classified into:
          - 6 `table`         (bt_q01 .. bt_q06)
          - 5 `image_diagram` (bt_q07 .. bt_q11)
          - 5 `chart`         (bt_q12 .. bt_q16)
          - 4 `multi_hop`     (bt_q17 .. bt_q20)
          - 4 `text`          (bt_q21 .. bt_q24)
      * 6 `unanswerable`      (bt_u01 .. bt_u06)
"""
from __future__ import annotations

import json
from typing import Any

from .bonus_ingest import BONUS_QUESTIONS_PATH, BONUS_SOURCE_ID


DEV_QUESTIONS: list[dict[str, Any]] = [
    # --- DEV: TABLE (3) ---
    {
        "id": "bd_q01",
        "split": "dev",
        "category": "table",
        "answerable": True,
        "question": "According to Table 4, what is the Clean-Coast Index (CCI) numeric index range and description for a beach graded as 'Moderate' versus 'Dirty', and what value is used for the coefficient k?",
        "expected_answer": "In Table 4 (Page 34), a 'Moderate' beach has a numeric index range of 5–10 ('A few pieces of waste were detected'), while a 'Dirty' beach has a numeric index range of 10–20 ('A lot of waste on shore/at sites'). The coefficient k used in the CCI equation is k = 20.",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 34,
                "asset_id": "table_04",
                "modality": "table",
                "bbox": [0.07, 0.44, 0.93, 0.62],
                "evidence": "coefficient k = 20",
            }
        ],
    },
    {
        "id": "bd_q02",
        "split": "dev",
        "category": "table",
        "answerable": True,
        "question": "In Table 8, what are the waste collection rates and the number of waste treatment facilities reported for Hai Phong City, Lao Cai/Sapa, and Hai Duong Province?",
        "expected_answer": "According to Table 8 (Page 57): (1) Hai Phong City has a 90% waste collection rate and 6–8 treatment facilities (one new) plus landfills; (2) Lao Cai/Sapa has an 85% waste collection rate and one treatment facility plus landfills; and (3) Hai Duong Province has an 80–85% waste collection rate and two treatment facilities plus landfills.",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 57,
                "asset_id": "table_08",
                "modality": "table",
                "bbox": [0.07, 0.08, 0.93, 0.88],
                "evidence": "6–8 treatment facilities",
            }
        ],
    },
    {
        "id": "bd_q03",
        "split": "dev",
        "category": "table",
        "answerable": True,
        "question": "According to Table 19, how many tons of Styrofoam floats for floating cages/rafts are sold per year in Vietnam, what is their average wholesale cost per unit and lifespan, and how does that compare to composite/HDPE floats for cages?",
        "expected_answer": "In Table 19 (Page 85), Styrofoam floats for floating cages/rafts sell 16,800 tons/year at an average wholesale cost of 380,000–550,000 VND/unit with a lifespan of 1–2 years. By comparison, composite/HDPE floats for cages sell 1,500 tons/year at 900,000–1,450,000 VND/unit and last 10–15 years.",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 85,
                "asset_id": "table_19",
                "modality": "table",
                "bbox": [0.07, 0.14, 0.93, 0.62],
                "evidence": "16,800 tons/year",
            }
        ],
    },

    # --- DEV: IMAGE / DIAGRAM (3) ---
    {
        "id": "bd_q04",
        "split": "dev",
        "category": "image_diagram",
        "answerable": True,
        "question": "In Figure 1 (and Figure 27), which specific pollution hotspot sites are shown in the four aerial drone photographs under the 'Hai Duong' and 'Hai Phong' columns?",
        "expected_answer": "In Figure 1 (Page 20) and Figure 27 (Page 66), the left column ('Hai Duong') displays two photographs labeled 'Hai Duong, Thach Khoi 1, site 1' (top) and 'Hai Duong, Thach Khoi 1, site 2' (bottom). The right column ('Hai Phong') displays two photographs labeled 'Chanh Duong 01 (6m), Site 1' (top) and 'Chanh Duong 02 (6m), site 2' (bottom).",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 20,
                "asset_id": "fig_01",
                "modality": "image_diagram",
                "bbox": [0.11, 0.11, 0.89, 0.48],
                "evidence": "Hai Duong, Thach Khoi 1, site 1",
            }
        ],
    },
    {
        "id": "bd_q05",
        "split": "dev",
        "category": "image_diagram",
        "answerable": True,
        "question": "What are the three field data collection devices depicted side-by-side in Figure 25 (Page 62)?",
        "expected_answer": "Figure 25 (Page 62) depicts three field monitoring devices from left to right: (1) stationary bridge cameras (GoPro mounted on a bridge railing pole configured via smartphone), (2) an unmanned aerial vehicle (UAV / white quadcopter drone) flying over a riverbank, and (3) a mobile net-sampling frame with blue trawl nets deployed vertically into the river water column beneath a bridge.",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 62,
                "asset_id": "fig_25",
                "modality": "image_diagram",
                "bbox": [0.08, 0.56, 0.92, 0.85],
                "evidence": "Figure 25: Data Collection Devices Utilized in the Field Work",
            }
        ],
    },
    {
        "id": "bd_q06",
        "split": "dev",
        "category": "image_diagram",
        "answerable": True,
        "question": "In Figure 51 (Page 125), what are the steel pipe diameter, net frame dimensions, and total additional ballast weight attached to the threaded bars of the newly developed macro-plastic equipment carrier?",
        "expected_answer": "According to Figure 51 and its accompanying specification on Page 125, the equipment carrier frame is built from 48 mm steel pipes, has macro-plastic measurement net frame dimensions of 600x600 mm, and uses 12 welded threaded bars each holding two ~10 kg weights for a total of 240 kg of additional ballast weight.",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 125,
                "asset_id": "fig_51",
                "modality": "image_diagram",
                "bbox": [0.08, 0.24, 0.92, 0.54],
                "evidence": "600x600 mm",
            }
        ],
    },

    # --- DEV: CHART (3) ---
    {
        "id": "bd_q07",
        "split": "dev",
        "category": "chart",
        "answerable": True,
        "question": "According to the pie-of-pie charts in Figure 5 and Figure 6 (Page 39), what percentage of total waste on surveyed sites in Vietnam was Plastic by total number of items versus by total weight, and how is the 'Other' slice broken down in each chart?",
        "expected_answer": "In Figure 5 (Page 39, by number of items), Plastic accounted for 93.6% of all waste items, while 'Other' (3.6%) broke down into Mix waste (1.5%), Cloth/fabric (1.5%), and Paper/timber (0.6%). In Figure 6 (Page 39, by weight), Plastic accounted for 70.7% of total waste weight, while 'Other' (14.1%) broke down into Mix waste (6.6%), Cloth/fabric (5.1%), and Paper/timber (2.4%).",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 39,
                "asset_id": "fig_05",
                "modality": "chart",
                "bbox": [0.14, 0.23, 0.86, 0.56],
                "evidence": "Plastic = 93.6%",
            },
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 39,
                "asset_id": "fig_06",
                "modality": "chart",
                "bbox": [0.14, 0.57, 0.86, 0.90],
                "evidence": "Plastic = 70.7%",
            },
        ],
    },
    {
        "id": "bd_q08",
        "split": "dev",
        "category": "chart",
        "answerable": True,
        "question": "In Figure 10 (Page 42), what percentage of plastic waste items were single-use plastics versus other plastic waste items at river sites compared to coastal sites?",
        "expected_answer": "According to Figure 10 (Page 42), at river sites single-use plastic waste items accounted for 72% (and other plastic waste items 28%), whereas at coastal sites single-use plastic waste items accounted for 52% (and other plastic waste items 48%).",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 42,
                "asset_id": "fig_10",
                "modality": "chart",
                "bbox": [0.10, 0.08, 0.90, 0.36],
                "evidence": "Single use waste items = 72%",
            }
        ],
    },
    {
        "id": "bd_q09",
        "split": "dev",
        "category": "chart",
        "answerable": True,
        "question": "In Figure 32 and Figure 33 (Page 108), what is the #1 most common plastic waste item (and its percentage share) at Red River sites versus at Mekong River sites?",
        "expected_answer": "In Figure 32 (Page 108), the #1 plastic waste item at Red River sites is 'Plastic bags size 1' at 44.7% of total plastic waste. In Figure 33 (Page 108), the #1 plastic waste item at Mekong River sites is 'Styrofoam food container' at 19.4% (followed by Plastic bags size 1 at 11.9%).",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 108,
                "asset_id": "fig_32",
                "modality": "chart",
                "bbox": [0.22, 0.19, 0.83, 0.50],
                "evidence": "Plastic bags size 1: 44.7%",
            },
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 108,
                "asset_id": "fig_33",
                "modality": "chart",
                "bbox": [0.22, 0.58, 0.83, 0.90],
                "evidence": "Styrofoam food container: 19.4%",
            },
        ],
    },

    # --- DEV: MULTI-HOP (3) ---
    {
        "id": "bd_q10",
        "split": "dev",
        "category": "multi_hop",
        "answerable": True,
        "question": "Combining Table 9 (Page 59) and Table 10 (Page 61), which survey site in Hai Phong had all four types of data analysis carried out (drone waste quantities, drone waste types, bridge camera transport, and net sampling), and what are its exact latitude and longitude coordinates?",
        "expected_answer": "In Table 10 (Page 61), 'Chanh Duong 2' (ID 2, located in Vinh Bao - Hai Phong) is the only site with all four analyses completed (Waste Quantities from drone surveys, Waste Types from drone surveys, Transport from two bridge camera surveys, and Waste Types from net sampling). In Table 9 (Page 59), the coordinates of Chanh Duong 2 (ID 2) are Latitude 20.641278 and Longitude 106.566986.",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 59,
                "asset_id": "table_09",
                "modality": "table",
                "bbox": [0.07, 0.14, 0.93, 0.52],
                "evidence": "20.641278",
            },
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 61,
                "asset_id": "table_10",
                "modality": "table",
                "bbox": [0.07, 0.42, 0.93, 0.88],
                "evidence": "Chanh Duong 2",
            },
        ],
    },
    {
        "id": "bd_q11",
        "split": "dev",
        "category": "multi_hop",
        "answerable": True,
        "question": "Comparing Figure 30 and Figure 31 (Page 71) with Table 14 (Page 72) for the net sampling at Chanh Duong 2, which waste category ranked #1 by quantity (number of pieces and %) versus #1 by weight (grams and %)?",
        "expected_answer": "By quantity (Figure 30 on Page 71 and Table 14 on Page 72), 'Packages and other wrapper' ranked #1 with 50 pieces out of 121 total plastic pieces (41.32%), followed by 'Plastic bag' with 37 pieces (30.58%). By weight (Figure 31 on Page 71 and Table 14 on Page 72), 'Organic waste' ranked #1 with 1,500 g out of 2,586 g total weight (58%), while among plastic categories 'Other plastic' was heaviest at 571 g (22%).",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 71,
                "asset_id": "fig_30",
                "modality": "chart",
                "bbox": [0.09, 0.08, 0.91, 0.44],
                "evidence": "41.32%",
            },
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 72,
                "asset_id": "table_14",
                "modality": "table",
                "bbox": [0.07, 0.08, 0.93, 0.91],
                "evidence": "1,500 g",
            },
        ],
    },
    {
        "id": "bd_q12",
        "split": "dev",
        "category": "multi_hop",
        "answerable": True,
        "question": "Across Table 15 (Page 78) and Table 16 (Page 79), which two of the Top 10 plastic waste items (and their ranks/percentages in Table 15) were excluded when forming the six product categories for the market alternatives analysis, and why?",
        "expected_answer": "In Table 15 (Page 78) and Page 79 (Table 16 context), the two excluded items were Rank #6 'Hard plastic fragments (HDPE)' (6.1%) and Rank #9 'Other plastic (plastic slippers, diapers, etc.)' (3.2%). They were excluded because they encompass a heterogeneous variety of materials and products, making areas of application and identification of specific market alternatives too ambiguous.",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 78,
                "asset_id": "table_15",
                "modality": "table",
                "bbox": [0.07, 0.44, 0.93, 0.88],
                "evidence": "Hard plastic fragments (HDPE)",
            },
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 79,
                "asset_id": "table_16",
                "modality": "table",
                "bbox": [0.07, 0.46, 0.93, 0.76],
                "evidence": "Categories for Market Alternatives Analysis",
            },
        ],
    },

    # --- DEV: TEXT (3) ---
    {
        "id": "bd_q13",
        "split": "dev",
        "category": "text",
        "answerable": True,
        "question": "According to Section 1 (Introduction, Page 26), how many million tons of plastic waste are discharged on land and into the oceans annually in Vietnam, and what percentages of domestic waste remain uncollected in urban versus rural areas?",
        "expected_answer": "According to Section 1 (Page 26), about 2.8 to 3.1 million tons of plastic waste are discharged on land annually in Vietnam, and an estimated 0.28 to 0.73 million tons are discharged into the oceans each year. Approximately 10-15 percent of waste is uncollected in urban areas versus 45-60 percent in rural areas, while only 10 percent is recovered through recycling or reuse and 71 percent is dumped in landfills (out of 64,500 tons/day or 23.5 million tons/year of domestic solid waste).",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 26,
                "asset_id": None,
                "modality": "text",
                "bbox": None,
                "evidence": "2.8 to 3.1 million tons",
            }
        ],
    },
    {
        "id": "bd_q14",
        "split": "dev",
        "category": "text",
        "answerable": True,
        "question": "According to Section 2.1.2.2 and 2.1.2.4 (Pages 32 and 34), how did the physical sampling unit definition and digging protocol differ between river sites and coastal sites?",
        "expected_answer": "At river sites, one sampling unit was defined as 1 m2 x 0.3 m depth (1 m length x 1 m width x 0.3 m depth), where survey teams dug down to a depth of 30 cm in a 1 m2 quadrat. At coastal sites, sampling did not involve digging (items >2.5 cm were collected from the surface along four random 5 m transects in a 100 m beach section) and one unit was defined as 1 m2 (1 m long x 1 m wide), surveyed on two consecutive days.",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 34,
                "asset_id": None,
                "modality": "text",
                "bbox": None,
                "evidence": "1m2 x 0.3m depth",
            }
        ],
    },
    {
        "id": "bd_q15",
        "split": "dev",
        "category": "text",
        "answerable": True,
        "question": "In the Waste Brand Audit subsection (Section 2.1.3.2, Page 42), out of the 24,461 waste items collected, how many items could be assigned to a brand, how many distinct brands did they represent, and what share of branded items did the top 21 brands comprise?",
        "expected_answer": "According to Page 42 (Waste Brand Audit), out of 24,461 waste items collected, 1,184 items could be assigned to one of 266 brands, and the 21 top brands comprised about 56 percent of the items assigned to a brand.",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 42,
                "asset_id": None,
                "modality": "text",
                "bbox": None,
                "evidence": "266 brands",
            }
        ],
    },

    # --- DEV: UNANSWERABLE (3) ---
    {
        "id": "bd_u01",
        "split": "dev",
        "category": "unanswerable",
        "answerable": False,
        "question": "What were the Clean-Coast Index (CCI) score and plastic density (items/m2) recorded for the beaches in Ha Long Bay (Quang Ninh Province) in Table 6?",
        "expected_answer": "Abstain: Ha Long Bay (Quang Ninh Province) was not among the 10 surveyed locations or 14 coastal sites in the report (Table 5 and Table 6 cover Hai Phong, Thua Thien Hue, Da Nang, Quang Nam, Nha Trang/Khanh Hoa, Ho Chi Minh, Soc Trang, and Phu Quoc).",
        "absence_reason": "Verified across Table 5 (pp.37–38), Figure 4 (p.35), and Table 6 (p.52): Quang Ninh / Ha Long Bay was never surveyed.",
        "gold": [],
    },
    {
        "id": "bd_u02",
        "split": "dev",
        "category": "unanswerable",
        "answerable": False,
        "question": "According to Table 13 and Table 14, how many pieces of floating plastic and what net-sampling flow velocity were recorded at Han Bridge in Hai Duong?",
        "expected_answer": "Abstain: According to Table 10 (Page 61), no drone, bridge camera, or net-sampling data analyses were completed or available for Han Bridge (ID 6) in Hai Duong, so Han Bridge does not appear in Table 13, Table 14, or Table 26.",
        "absence_reason": "Verified in Table 10 (p.61): Row 6 (Han bridge, Hai Duong) has blank cells for all four monitoring methods.",
        "gold": [],
    },
    {
        "id": "bd_u03",
        "split": "dev",
        "category": "unanswerable",
        "answerable": False,
        "question": "What is the exact chemical leaching rate of bisphenol A (BPA) and phthalates in nanograms per liter (ng/L) measured from the river water samples in the Mekong and Red Rivers?",
        "expected_answer": "Abstain: The report focuses on macro-plastic litter surveys, remote sensing/net trawl monitoring, and market alternatives; it does not measure dissolved chemical leaching concentrations of BPA or phthalates in ng/L in river water.",
        "absence_reason": "Full-text search across all 138 pages confirms zero mentions of bisphenol A, BPA, phthalates, or ng/L chemical water analysis.",
        "gold": [],
    },
]


TEST_QUESTIONS: list[dict[str, Any]] = [
    # =========================================================================
    # TEST: TABLE (6 questions: bt_q01 .. bt_q06)
    # =========================================================================
    {
        "id": "bt_q01",
        "split": "test",
        "category": "table",
        "answerable": True,
        "question": "According to Table 6 (Page 52), which coastal site had the highest Clean-Coast Index (CCI) and which coastal site had the lowest CCI? State the exact density (item/m2), weight (g/m2), CCI value, and rating for both sites.",
        "expected_answer": "In Table 6 (Page 52): (1) The highest CCI was at Binh Lap (Nha Trang / Khanh Hoa) with a density of 18.9 items/m2, weight of 76.7 g/m2, CCI of 379.8, and rating 'Extremely Dirty'. (2) The lowest CCI was at Ho Be (Soc Trang) with a density of 0.39 items/m2, weight of 3.63 g/m2, CCI of 7.80, and rating 'Moderate'.",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 52,
                "asset_id": "table_06",
                "modality": "table",
                "bbox": [0.07, 0.08, 0.93, 0.56],
                "evidence": "379.8",
            }
        ],
    },
    {
        "id": "bt_q02",
        "split": "test",
        "category": "table",
        "answerable": True,
        "question": "In Table 11 (Page 65), how many assessed waste items, what waste area (m2), and what volume (m3) were recorded for the two pollution hotspots at Thach Khoi 1 in Hai Duong (individually and combined), and what were the corrected waste item numbers for Suoi Cat 01_1 and Suoi Cat 01_2?",
        "expected_answer": "According to Table 11 (Page 65): 'Hai Duong, Thach Khoi 1, site 1' had 2,986 assessed waste items, 25 m2 waste area, and 6 m3 volume; 'Hai Duong, Thach Khoi 1, site 2' had 2,521 assessed waste items, 20 m2 waste area, and 5 m3 volume (combined = 5,507 assessed waste items, 45 m2 area, and 11 m3 volume). For Sapa, 'Suoi Cat 01_1' had 857 assessed items and 296 corrected items, while 'Suoi Cat 01_2' had 378 assessed items and 116 corrected items (combined = 412 corrected items).",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 65,
                "asset_id": "table_11",
                "modality": "table",
                "bbox": [0.07, 0.34, 0.93, 0.77],
                "evidence": "2,986",
            }
        ],
    },
    {
        "id": "bt_q03",
        "split": "test",
        "category": "table",
        "answerable": True,
        "question": "According to Table 13 (Page 69), what were the total floating plastic item counts (SUM row, including any 600m-extrapolated figures in parentheses) recorded across the monitoring day for each of the five monitored bridges?",
        "expected_answer": "In Table 13 (Page 69), the SUM row across the five bridges is: (1) Hai Duong, Thach Khoi 2 = 236; (2) Hai Phong, Chanh Duong 01 = 286 (600); (3) Hai Phong, Chanh Duong 02 = 465 (600); (4) Hai Phong, Dang bridge = 140; and (5) Sapa, Suoi Cat 2 = 360.",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 69,
                "asset_id": "table_13",
                "modality": "table",
                "bbox": [0.07, 0.08, 0.93, 0.91],
                "evidence": "465 (600)",
            }
        ],
    },
    {
        "id": "bt_q04",
        "split": "test",
        "category": "table",
        "answerable": True,
        "question": "In Table 17 (Pages 81–82), what are the estimated annual tons sold and average wholesale cost per kg for PE bags, HDPE plastic bags, and compostable plastic bags?",
        "expected_answer": "According to Table 17 (Pages 81–82): (1) PE bags (various sizes): 284,692 tons/year at 30,000–40,000 VND/kg; (2) HDPE plastic bags (various sizes): 360,000 tons/year at 36,000–48,000 VND/kg; and (3) Compostable plastic bags (various sizes): 51,897 tons/year at 160,000 VND/kg (single-use).",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 81,
                "asset_id": "table_17",
                "modality": "table",
                "bbox": [0.07, 0.46, 0.93, 0.92],
                "evidence": "284,692 tons",
            }
        ],
    },
    {
        "id": "bt_q05",
        "split": "test",
        "category": "table",
        "answerable": True,
        "question": "According to Table 21 (Page 88), how many million pieces per year and at what average wholesale cost per unit are Straight PP plastic straws and U-shaped PP straws for dairy factories sold, and what are the annual volumes sold for Paper/kraft straws, Rice/vegetable straws, Grass straws, and Bamboo/wooden straws?",
        "expected_answer": "In Table 21 (Page 88): Straight PP plastic straws sell 1,257 million pcs/year at 200–1,000 VND/unit, and U-shaped PP plastic straws for dairy factories sell 2,560 million pcs/year at 100–300 VND/unit. Among alternatives to straight straws: Paper/kraft straws sell 850 million pcs/year (200–500 VND/unit), Rice/vegetable straws sell 580 million pcs/year (300–800 VND/unit), Grass straws sell 85 million pcs/year (400–500 VND/unit), and Bamboo/wooden straws sell 65 million pcs/year (600–1,000 VND/unit wholesale; 1,000–6,000 VND/unit retail). Additionally, U-shaped paper/sugarcane fiber straws sell 680 million pcs/year (400 VND/unit).",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 88,
                "asset_id": "table_21",
                "modality": "table",
                "bbox": [0.07, 0.24, 0.93, 0.88],
                "evidence": "1,257 million",
            }
        ],
    },
    {
        "id": "bt_q06",
        "split": "test",
        "category": "table",
        "answerable": True,
        "question": "In Table 26 (Page 130), what were the exact upper-net and lower-net flow velocities (in m/s) measured at Pos. 1 (GOPRO2), Pos. 2 (GOPRO1), and Pos. 3 (GOPRO3) across all six measurement timestamps?",
        "expected_answer": "According to Table 26 (Page 130): (1) 8:30 AM at Pos. 2 (GOPRO1): Upper net = 0.26 m/s, Lower net = 0.18 m/s; (2) 9:40 AM at Pos. 1 (GOPRO2): Upper net = 0.35 m/s, Lower net = 0.24 m/s; (3) 10:20 AM at Pos. 1 (GOPRO2): Upper net = 0.41 m/s, Lower net = 0.27 m/s; (4) 11:30 AM at Pos. 2 (GOPRO1): Upper net = 0.43 m/s, Lower net = 0.30 m/s; (5) 1:20 PM at Pos. 3 (GOPRO3): Upper net = 0.58 m/s, Lower net = 0.36 m/s; and (6) 2:25 PM at Pos. 3 (GOPRO3): Upper net = 0.63 m/s, Lower net = 0.41 m/s.",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 130,
                "asset_id": "table_26",
                "modality": "table",
                "bbox": [0.07, 0.16, 0.93, 0.52],
                "evidence": "0.63 m/s",
            }
        ],
    },

    # =========================================================================
    # TEST: IMAGE / DIAGRAM (5 questions: bt_q07 .. bt_q11)
    # =========================================================================
    {
        "id": "bt_q07",
        "split": "test",
        "category": "image_diagram",
        "answerable": True,
        "question": "In the map in Figure 4 (Page 35), list all 10 surveyed locations and the exact River (R) and Coastal (C) site counts printed inside their orange callout labels, and identify which two locations on the map have only River (R) sites.",
        "expected_answer": "In Figure 4 (Page 35), the 10 callout labels are: Lao Cai (R: 4), Hai Phong (R: 2, C: 2), Thua Thien Hue (R: 2, C: 1), Da Nang (R: 4, C: 2), Quang Nam (R: 2, C: 1), Khanh Hoa (R: 3, C: 3), Phu Quoc (R: 2, C: 2), Ho Chi Minh (R: 2, C: 1), Can Tho (R: 3), and Soc Trang (R: 2, C: 2). The two locations with only River (R) sites and zero Coastal sites are Lao Cai (R: 4) and Can Tho (R: 3).",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 35,
                "asset_id": "fig_04",
                "modality": "image_diagram",
                "bbox": [0.11, 0.12, 0.89, 0.90],
                "evidence": "Lao Cai (R: 4)",
            }
        ],
    },
    {
        "id": "bt_q08",
        "split": "test",
        "category": "image_diagram",
        "answerable": True,
        "question": "In Figure 26 (Page 63, 'Example of a Typical Survey Protocol'), which bridge and river are shown on the schematic map, what are the exact dimensions (in meters) of the high-altitude flight area and low-altitude survey boxes, and was an actual survey conducted at this bridge?",
        "expected_answer": "Figure 26 (Page 63) shows Cau Rao Bridge crossing the Lach Tray River in Hai Phong (scale 1:3,800). The high-altitude flight area (captured at 60–100 m altitude) extends 250 m upstream and 250 m downstream of the bridge (500 m total length) with upper and lower edges fixed at 100 m from the riverbanks. The low-altitude flight areas (captured at 3–6 m altitude) are 10 m x 10 m survey boxes ('10 x 10m survey box'). As stated in the note beneath Figure 26, no actual survey was undertaken at Cau Rao Bridge (it is shown purely as an example of a typical survey protocol).",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 63,
                "asset_id": "fig_26",
                "modality": "image_diagram",
                "bbox": [0.08, 0.41, 0.92, 0.86],
                "evidence": "Cau Rao Bridge",
            }
        ],
    },
    {
        "id": "bt_q09",
        "split": "test",
        "category": "image_diagram",
        "answerable": True,
        "question": "According to Figure 47 (Page 118), what are the three vertical sampling layers of the net trawl device, and what exact frame opening dimensions (in mm) and net mesh sizes (in um) are specified in the diagram for each of the three layers?",
        "expected_answer": "In Figure 47 (Page 118), the three vertical layers and their diagram callout specifications are: (1) 'Water surface sampling' (top): openings 600x600 mm, nets 500 um and 250 um, buoyant bodies, fins, inclination rack, mechanical flow meter; (2) 'Middle of water column' (middle): openings 600x600 mm, nets 500 um, 250 um, and optional 41 um net, fins, inclination rack, mechanical flow meter; and (3) 'Near-bed sampling' (bottom): basket sampler, heavy loads, opening 300x600 mm, net 500 um, fins, mechanical flow meter.",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 118,
                "asset_id": "fig_47",
                "modality": "image_diagram",
                "bbox": [0.24, 0.22, 0.75, 0.73],
                "evidence": "Water surface sampling",
            }
        ],
    },
    {
        "id": "bt_q10",
        "split": "test",
        "category": "image_diagram",
        "answerable": True,
        "question": "In Figure 48 (Page 119), what are the two convolutional neural network components of the APLASTIC-Q pipeline, what six classes does the first CNN output, and what pollution fraction and average thickness are assumed for 'Litter-low' versus 'Litter-high' tiles when calculating waste area and volume?",
        "expected_answer": "In Figure 48 (Page 119), the two CNN components are PLD-CNN (Plastic Litter Detection CNN, processing 128x128x3 tiles / 100x100x3 in diagram) and PLQ-CNN (Plastic Litter Quantification CNN, processing 64x64x3 tiles / 50x50x3 in diagram). PLD-CNN classifies tiles into six classes: Water, Vegetation, Sand, Litter-high, Litter-low, and Other. For waste area and volume calculations, 'Litter-low' tiles are considered 50% polluted with an average thickness of 7 cm, while 'Litter-high' tiles are considered 100% polluted with an average thickness of 30 cm.",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 119,
                "asset_id": "fig_48",
                "modality": "image_diagram",
                "bbox": [0.08, 0.42, 0.92, 0.72],
                "evidence": "PLD-CNN",
            }
        ],
    },
    {
        "id": "bt_q11",
        "split": "test",
        "category": "image_diagram",
        "answerable": True,
        "question": "In the APLASTIC-Q example output in Figure 49 (Page 120, scene 'parola_phantomq1_transparent_mosaic_group1'), how many Litter-high tiles, Litter-low tiles, estimated total items ('Est. no. of items'), estimated polluted area ('m2 est.'), and estimated waste volume ('m3 est.') are reported in the PLD CNN table, and what are the top three waste types in the 'Share of waste types' pie chart?",
        "expected_answer": "In Figure 49 (Page 120), the PLD CNN table reports: Litter-high = 377, Litter-low = 746, Est. no. of items = 3,377, m2 est. = 30 m2, and m3 est. = 6 m3 (along with Other = 156, Sand = 676, Vegetation = 1,273, Water = 326). In the 'Share of waste types' pie chart, the top three waste types are: (1) P - cup lids, caps and small plastics (45%), (2) P - polystyrene under 20cm (15%), and (3) NP - other (13%).",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 120,
                "asset_id": "fig_49",
                "modality": "image_diagram",
                "bbox": [0.08, 0.45, 0.92, 0.86],
                "evidence": "3,377",
            }
        ],
    },

    # =========================================================================
    # TEST: CHART (5 questions: bt_q12 .. bt_q16)
    # =========================================================================
    {
        "id": "bt_q12",
        "split": "test",
        "category": "chart",
        "answerable": True,
        "question": "In Figure 2 (Page 20, repeated as Figure 14 on Page 45), which plastic waste item ranked #1 by density on riverbanks and which item ranked #1 by weight on riverbanks? Provide both the density percentage and weight percentage for each of those two items.",
        "expected_answer": "In Figure 2 (Page 20) and Figure 14 (Page 45), 'Plastic bags size 1' ranked #1 by density on riverbanks with 21.9% of density and 14% of weight (2nd in weight). By weight, 'Hard plastic fragments' ranked #1 on riverbanks with 15% of weight, even though it ranked 8th in density at 4.6%.",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 20,
                "asset_id": "fig_02",
                "modality": "chart",
                "bbox": [0.12, 0.51, 0.88, 0.88],
                "evidence": "21.9%",
            }
        ],
    },
    {
        "id": "bt_q13",
        "split": "test",
        "category": "chart",
        "answerable": True,
        "question": "According to Figure 7 (Page 40), what are the exact percentage shares of the five plastic waste sources by Number versus by Weight across all surveyed sites in Vietnam in 2020?",
        "expected_answer": "In Figure 7 (Page 40): By Number: (1) Take-away related = 43.6%, (2) Fisheries-related = 32.6%, (3) Household = 21.6%, (4) Agriculture-related = 1.1%, and (5) Sanitary and Medical-related = 1.1%. By Weight: (1) Take-away related = 35.1%, (2) Fisheries-related = 30.6%, (3) Household = 22.8%, (4) Agriculture-related = 8.2%, and (5) Sanitary and Medical-related = 3.3%.",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 40,
                "asset_id": "fig_07",
                "modality": "chart",
                "bbox": [0.08, 0.10, 0.92, 0.44],
                "evidence": "43.6%",
            }
        ],
    },
    {
        "id": "bt_q14",
        "split": "test",
        "category": "chart",
        "answerable": True,
        "question": "In Figure 15 (Page 46, 'Top 10 Plastic Waste Items at River Sites in Rural and Urban Areas by Density'), what are the top three items and their percentages in Rural river sites versus Urban river sites, and which single item appears only in the Rural river Top 10 versus only in the Urban river Top 10?",
        "expected_answer": "In Figure 15 (Page 46): At Rural river sites, the top three items are Plastic bags size 1 (20.6%), Styrofoam food container (13.5%), and Plastic strings, cords and ropes (9.5%, tied with Food wrappers at 9.5%). At Urban river sites, the top three items are Plastic bags size 1 (22.4%), Soft plastic fragment (11.3%), and Styrofoam food container (10.6%). The item unique to the Rural river Top 10 is 'Fertilizer Bags or containers' (3.5%, ranked 9th), while the item unique to the Urban river Top 10 is 'Other wrappers' (4.7%, ranked 7th).",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 46,
                "asset_id": "fig_15",
                "modality": "chart",
                "bbox": [0.09, 0.25, 0.91, 0.55],
                "evidence": "Fertilizer Bags or containers: 3.5%",
            }
        ],
    },
    {
        "id": "bt_q15",
        "split": "test",
        "category": "chart",
        "answerable": True,
        "question": "In Figure 23 (Page 51, 'Single-use Plastic Waste Density at Coastal Sites in Surveyed Locations'), what are the exact 'Single use' and 'Other' plastic waste density values (in Item.unit^-1) for all eight coastal locations, and which location had the highest Single-use density versus the highest Other density?",
        "expected_answer": "In Figure 23 (Page 51), the exact density values (Single use vs. Other, in Item.unit^-1) across the 8 coastal locations are: Da Nang (10.5 vs. 17.3), Hai Phong (15.4 vs. 20.8), Ho Chi Minh (57.4 vs. 78.5), Hue (67.3 vs. 73.8), Khanh Hoa (50.2 vs. 30.6), Phu Quoc (34.4 vs. 33.8), Quang Nam (70.1 vs. 63.6), and Soc Trang (50.4 vs. 29.6). Quang Nam had the highest Single-use plastic density (70.1 Item.unit^-1), while Ho Chi Minh had the highest Other plastic density (78.5 Item.unit^-1).",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 51,
                "asset_id": "fig_23",
                "modality": "chart",
                "bbox": [0.16, 0.53, 0.84, 0.83],
                "evidence": "70.1",
            }
        ],
    },
    {
        "id": "bt_q16",
        "split": "test",
        "category": "chart",
        "answerable": True,
        "question": "In Figure 29 (Page 70, 'Waste transport over the course of the day for Hai Phong, Chanh Duong 02 bridge'), at what exact time of day does Camera 01 reach its highest peak (and approximately how many items), at what time does Camera 02 reach its morning peak, and at what afternoon timestamp do both cameras experience a simultaneous secondary peak?",
        "expected_answer": "In Figure 29 (Page 70): Camera 01 (blue line) reaches its highest daily peak at 10:30 with approximately 33 items (before dropping sharply to 5 items at 11:30). Camera 02 (orange line) reaches its morning peak at 11:00 with approximately 25 items (after a low of 1 item at 10:00). Both Camera 01 and Camera 02 experience a simultaneous afternoon peak at 14:00 (approx. 22 items on Camera 01 and 20 items on Camera 02) before declining toward 16:30.",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 70,
                "asset_id": "fig_29",
                "modality": "chart",
                "bbox": [0.16, 0.08, 0.84, 0.38],
                "evidence": "10:30",
            }
        ],
    },

    # =========================================================================
    # TEST: MULTI-HOP (4 questions: bt_q17 .. bt_q20)
    # =========================================================================
    {
        "id": "bt_q17",
        "split": "test",
        "category": "multi_hop",
        "answerable": True,
        "question": "Comparing the three coastal subzones in Figure 38 (Page 112) and Figures 39–40 (Page 113), which plastic item is #1 in standing stock density in the Northern subzone versus in the Transitional and Southern subzones, and how does the standing stock share of 'Styrofoam food containers' differ across the three subzones?",
        "expected_answer": "In the Northern subzone (Figure 38, Page 112: Hai Phong and Thua Thien Hue), 'Fishing gear 1: Fishing Plastic' is #1 in standing stock density at 22.3% (17.0% in 1-day accumulation), whereas in both the Transitional subzone (Figure 39, Page 113: Da Nang, Quang Nam, Khanh Hoa) and the Southern subzone (Figure 40, Page 113: Ho Chi Minh, Soc Trang, Phu Quoc), 'Soft plastic fragment' is #1 in standing stock density at 21.7% and 19.9%, respectively. Meanwhile, 'Styrofoam food containers' ranked 4th in the Southern subzone (11.7% on chart / 10.1% in text, and 15.3% of 1-day accumulation) and 6th in the Transitional subzone (4.4% standing stock, 4.6% 1-day accumulation), but did not even make the Top 10 in the Northern subzone (accounting for only 1.4%).",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 112,
                "asset_id": "fig_38",
                "modality": "chart",
                "bbox": [0.18, 0.24, 0.91, 0.65],
                "evidence": "22.3%",
            },
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 113,
                "asset_id": "fig_39",
                "modality": "chart",
                "bbox": [0.14, 0.10, 0.86, 0.44],
                "evidence": "21.7%",
            },
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 113,
                "asset_id": "fig_40",
                "modality": "chart",
                "bbox": [0.14, 0.48, 0.86, 0.86],
                "evidence": "19.9%",
            },
        ],
    },
    {
        "id": "bt_q18",
        "split": "test",
        "category": "multi_hop",
        "answerable": True,
        "question": "Synthesizing Figure 28 (Page 67), Table 12 (Page 68), and Table 25 (Page 128), what is the overall share and item count of Polystyrene across all drone survey sites, how do the Polystyrene vs. LDPE bag proportions compare between Hai Duong, Hai Phong, and Sapa (Figure 28 & Table 12), and which individual hotspot in Table 25 had the highest share of LDPE bags ('Bags LDPE')?",
        "expected_answer": "Across all drone survey sites (Figure 28D on Page 67 and Table 12 on Page 68), Polystyrene is the #1 waste type at 40% combined (1,735 items under 20cm [38%] + 123 items over 20cm [3%] = 1,858 items out of 4,618 total items). By city (Figure 28A–C and Table 12): in Hai Duong, Polystyrene is 43% (40% under 20cm + 3% over 20cm) while LDPE bags are only 3%; in Hai Phong, Polystyrene is 30% (28% + 2%) while LDPE bags rise to 26% (23% Bags LDPE + 3% Bags LDPE thick); in Sapa, Polystyrene is 18% and LDPE bags are 17% (13% Bags LDPE + 3% Bags LDPE thick in Table 12), behind Other non-plastics at 19%. In Table 25 (Page 128), the individual hotspot with the highest share of 'Bags LDPE' is 'Hai Phong, Chanh Duong 02, site 2' at 49% (plus 3% thick LDPE bags = 52% total LDPE bags), followed by 'Hai Phong, Chanh Duong 01, Site 3' at 38%.",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 67,
                "asset_id": "fig_28",
                "modality": "chart",
                "bbox": [0.08, 0.36, 0.92, 0.82],
                "evidence": "Polystyrene = 43%",
            },
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 68,
                "asset_id": "table_12",
                "modality": "table",
                "bbox": [0.07, 0.08, 0.93, 0.72],
                "evidence": "1,735",
            },
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 128,
                "asset_id": "table_25",
                "modality": "table",
                "bbox": [0.07, 0.14, 0.93, 0.91],
                "evidence": "49%",
            },
        ],
    },
    {
        "id": "bt_q19",
        "split": "test",
        "category": "multi_hop",
        "answerable": True,
        "question": "Compare the Single-Use Plastic (SUP) density and percentage share for Soc Trang and Can Tho between the River sites (Table 24 & Figure 37 on Page 111, and text on Page 110) and the Coastal sites (Figure 23 on Page 51).",
        "expected_answer": "At River sites (Table 24 & Figure 37 on Page 111, text on Page 110): Can Tho had the highest single-use plastic density of all 10 river locations at 24.9 items/unit (with 9.7 items/unit Other = 34.5 items/unit total, or 72% SUP), whereas Soc Trang had the lowest river single-use plastic density at 4.0 items/unit (with 0.3 items/unit Other = 4.3 items/unit total) but the highest river SUP percentage share at 93%. At Coastal sites (Figure 23 on Page 51): Can Tho has no coastal sites (it is a river-only location), whereas Soc Trang's coastal sites had a much higher single-use plastic density of 50.4 items/unit (and 29.6 items/unit Other = 80.0 items/unit total), representing 63% SUP — again the highest SUP percentage share among the coastal locations.",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 111,
                "asset_id": "table_24",
                "modality": "table",
                "bbox": [0.07, 0.42, 0.93, 0.86],
                "evidence": "24.9",
            },
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 51,
                "asset_id": "fig_23",
                "modality": "chart",
                "bbox": [0.16, 0.53, 0.84, 0.83],
                "evidence": "50.4",
            },
        ],
    },
    {
        "id": "bt_q20",
        "split": "test",
        "category": "multi_hop",
        "answerable": True,
        "question": "Using Table 7 (Page 54), Figure 3 (Page 21), and Table 18 (Page 84), what share of coastal plastic waste by density and by weight is accounted for by 'Fishing gear 1', what are the three fishing net subcategories and their annual tons sold and wholesale costs per m2 in Table 18, and what are the wholesale costs per m2 of their three non-plastic/biodegradable alternatives?",
        "expected_answer": "In Table 7 (Page 54) and Figure 3 (Page 21), 'Fishing gear 1' (plastic rope, net pieces, fishing lures & lines, hard plastic floats) is the #1 polluting plastic item at coastal sites, accounting for 18.5% by density (number) and 19.1% by weight. In Table 18 (Page 84), the three fishing net subcategories and their alternatives are: (1) Parachute fishing net (mesh 1.5–40 cm): 45,054 tons/year at 20,800–25,000 VND/m2 (durability 4–6 years) vs. Biodegradable net at 70,000–138,000 VND/m2 (decomposes after 6 months in water); (2) Traditional fishing net (mesh 2–12 cm): 29,212 tons/year at 2,160–7,630 VND/m2 (durability 6 months–3 years) vs. Coir net at 22,000–25,000 VND/m2 (durability 1–2 years); and (3) Aquaculture net (mesh 0.2–5 cm): 14,500 tons/year at 3,000–15,000 VND/m2 (durability 2–5 years) vs. Metal wire net at 32,000–100,000 VND/m2 (durability 3–5 years).",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 21,
                "asset_id": "fig_03",
                "modality": "chart",
                "bbox": [0.13, 0.11, 0.87, 0.44],
                "evidence": "19.1%",
            },
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 54,
                "asset_id": "table_07",
                "modality": "table",
                "bbox": [0.07, 0.08, 0.93, 0.62],
                "evidence": "18.5%",
            },
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 84,
                "asset_id": "table_18",
                "modality": "table",
                "bbox": [0.07, 0.14, 0.93, 0.58],
                "evidence": "45,054 tons",
            },
        ],
    },

    # =========================================================================
    # TEST: TEXT (4 questions: bt_q21 .. bt_q24)
    # =========================================================================
    {
        "id": "bt_q21",
        "split": "test",
        "category": "text",
        "answerable": True,
        "question": "According to the Executive Summary (Page 23) and Section 3: Way Forward (Pages 92–93), what four core recommendation areas and specific SUP policy instruments (including target take-away items and sector focus) does the report propose for Vietnam?",
        "expected_answer": "On Page 23 and in Section 3 (Pages 92–93), the report proposes four main action areas: (1) Integrated plastics monitoring using low-cost surveys, piloted river remote-sensing/bridge cameras paired with net trawls, and MONRE monitoring guidelines; (2) A policy roadmap for low-value and single-use plastic (SUP) waste—including phasing in bans, restrictions, and taxes/fees on priority SUPs such as plastic bags and take-away food packaging (Styrofoam, plastic cutlery, straws, and drink-stirrers) common in tourism and retail, plus levies, design requirements, EPR schemes, and standards for alternatives; (3) Fisheries- and aquaculture-related measures (ports, aquaculture, capture fisheries) supporting MARD's Action Plan for Marine Plastic Waste Management in the Fisheries Sector; and (4) Public awareness and youth education targeting the top 10 polluting plastic items.",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 23,
                "asset_id": None,
                "modality": "text",
                "bbox": None,
                "evidence": "extended producer responsibility (EPR)",
            },
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 92,
                "asset_id": None,
                "modality": "text",
                "bbox": None,
                "evidence": "Styrofoam",
            },
        ],
    },
    {
        "id": "bt_q22",
        "split": "test",
        "category": "text",
        "answerable": True,
        "question": "According to Section 2.1.2.5 (Limitations, Page 34), which monsoon season were the field surveys originally planned for, over what actual period were they conducted due to COVID-19 delays, and how many locations were not surveyed in the same monsoon season?",
        "expected_answer": "According to Section 2.1.2.5 (Page 34), the field surveys were originally planned to take place during the Southwest Monsoon season (May–October). Due to COVID-19 pandemic restrictions and rescheduling, the surveys were actually conducted from July 2020 to January 2021 across two monsoon seasons (Southwest and Northeast Monsoons), and 11 locations were not surveyed in the same monsoon season.",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 34,
                "asset_id": None,
                "modality": "text",
                "bbox": None,
                "evidence": "July 2020 to January 2021",
            }
        ],
    },
    {
        "id": "bt_q23",
        "split": "test",
        "category": "text",
        "answerable": True,
        "question": "According to Annex 2.2.A (Page 122), what is the mathematical equation for the plastic transport rate q_{i,j} (including the exact units of each variable), and what is the name of the 3D hydrodynamic numerical model developed by BOKU/IWA?",
        "expected_answer": "On Page 122 (Equation 2), the plastic transport rate is q_{i,j} = C_{i,j} * v_{i,j}, where q_{i,j} is the transport rate in [g m^-2 s^-1], C_{i,j} is the plastic concentration in [g m^-3], and v_{i,j} is the measured flow velocity in [m s^-1]. The three-dimensional hydrodynamic numerical model developed by BOKU/IWA is R-Sim3D (Tritthart and Gutknecht, 2007), which solves the Reynolds-averaged Navier-Stokes equations using the Finite Volume Method on a polyhedral mesh with k-epsilon and k-omega turbulence closure models.",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 122,
                "asset_id": None,
                "modality": "text",
                "bbox": None,
                "evidence": "R-Sim3D",
            }
        ],
    },
    {
        "id": "bt_q24",
        "split": "test",
        "category": "text",
        "answerable": True,
        "question": "According to Annex 2.2.B ('Mesh size', Page 125), what four net mesh sizes (and their porosity percentages) were tested during the project, what net length was calculated to achieve an 'open area ratio' of three for the 250 um and 500 um nets, and which mesh size is recommended for macro-plastic sampling?",
        "expected_answer": "According to Annex 2.2.B (Page 125), the four tested mesh sizes and their porosities were: (1) 250 um with 34% porosity, (2) 500 um with 38% porosity, (3) 2.43 mm (2,43 mm) with 44% porosity, and (4) 8 mm with very high but undefined porosity. To reach the required 'open area ratio' of three (Tranter and Smith, 1968), a net length of 2.5 m (2,5 m) was calculated and used for the 250 um and 500 um nets (and the coarser meshes were built with the same dimensions). The 2.43 mm mesh net is recommended for macro-plastic sampling because it provides significantly better filtration efficiency and longer measuring times under high suspended-matter loads while covering the full macro-plastic size range (unlike the 8 mm net).",
        "gold": [
            {
                "source_id": BONUS_SOURCE_ID,
                "page": 125,
                "asset_id": None,
                "modality": "text",
                "bbox": None,
                "evidence": "250 um with 34 % porosity",
            }
        ],
    },

    # =========================================================================
    # TEST: UNANSWERABLE (6 questions: bt_u01 .. bt_u06)
    # =========================================================================
    {
        "id": "bt_u01",
        "split": "test",
        "category": "unanswerable",
        "answerable": False,
        "question": "According to Table 6 and Figure 23, what were the Clean-Coast Index (CCI) score and single-use plastic density (items/m2) measured at the coastal beaches in Vung Tau (Ba Ria - Vung Tau Province) and Quy Nhon (Binh Dinh Province)?",
        "expected_answer": "Abstain: Neither Vung Tau (Ba Ria - Vung Tau) nor Quy Nhon (Binh Dinh) was among the 10 surveyed locations or 14 coastal sites in the study (Table 5, Table 6, and Figure 23 only cover Hai Phong, Thua Thien Hue, Da Nang, Quang Nam, Nha Trang/Khanh Hoa, Ho Chi Minh City, Soc Trang, and Phu Quoc).",
        "absence_reason": "Verified across Table 5 (pp.37–38), Table 6 (p.52), and Figure 23 (p.51): Vung Tau and Quy Nhon were not surveyed.",
        "gold": [],
    },
    {
        "id": "bt_u02",
        "split": "test",
        "category": "unanswerable",
        "answerable": False,
        "question": "In Table 11 and Table 25, how many waste items and what percentage of Polystyrene were detected by the drone survey at the Suoi Cat 3 hotspot in Sapa?",
        "expected_answer": "Abstain: According to Table 10 (Page 61), no drone survey, bridge camera, or net-sampling data analyses were available for Suoi Cat 3 (ID 9) in Sapa; Table 11 and Table 25 only report drone hotspot results for Suoi Cat 01_1 and Suoi Cat 01_2.",
        "absence_reason": "Verified in Table 10 (p.61), Table 11 (p.65), and Table 25 (pp.128–129): Suoi Cat 3 had no completed analysis.",
        "gold": [],
    },
    {
        "id": "bt_u03",
        "split": "test",
        "category": "unanswerable",
        "answerable": False,
        "question": "According to Table 18 (Page 84), how many tons per year of Biodegradable fishing nets, Coir nets, and Metal wire nets are sold in Vietnam?",
        "expected_answer": "Abstain: In Table 18 (Page 84), the 'Units sold per year (estimate)' column for Biodegradable net, Coir net, and Metal wire net is explicitly marked as 'N/A' (not available); only their average wholesale costs per m2 and durability are reported.",
        "absence_reason": "Verified in Table 18 (p.84): Units sold per year for Biodegradable net, Coir net, and Metal wire net are all 'N/A'.",
        "gold": [],
    },
    {
        "id": "bt_u04",
        "split": "test",
        "category": "unanswerable",
        "answerable": False,
        "question": "In Figure 29 (Page 70), what were the nighttime floating plastic transport counts recorded by Camera 01 and Camera 02 at Chanh Duong 02 bridge between 18:00 and 06:00?",
        "expected_answer": "Abstain: Figure 29 (Page 70) only plots daytime floating plastic transport at Chanh Duong 02 bridge from 08:30 to 16:30 (an 8-hour daytime monitoring window); no nighttime counts between 18:00 and 06:00 were recorded or plotted.",
        "absence_reason": "Verified in Figure 29 (p.70) and Annex 2.2.A (p.116): Camera monitoring lasted 8 hours during daylight (08:30–16:30); no nighttime data exist.",
        "gold": [],
    },
    {
        "id": "bt_u05",
        "split": "test",
        "category": "unanswerable",
        "answerable": False,
        "question": "According to the gastrointestinal tract necropsy data in Section 2.1, what was the average number of ingested microplastic particles per fish across commercial marine fish species sampled in Vietnam?",
        "expected_answer": "Abstain: The report does not conduct biological fish necropsy or measure ingested microplastic particles per fish in commercial marine species; its field surveys only collected macro-litter (>2.5 cm) on riverbanks and beaches and river water-column debris.",
        "absence_reason": "Full-text verification across all 138 pages confirms no fish necropsy or biological microplastic ingestion data.",
        "gold": [],
    },
    {
        "id": "bt_u06",
        "split": "test",
        "category": "unanswerable",
        "answerable": False,
        "question": "What were the 2023 and 2024 post-implementation compliance rates and tax revenues (in billion VND) collected under Vietnam's Extended Producer Responsibility (EPR) decree in Section 3?",
        "expected_answer": "Abstain: The report was published in June 2022 (using 2020–2021 diagnostic data) before EPR implementation took effect, so it contains no 2023 or 2024 post-implementation EPR compliance rates or tax revenue figures.",
        "absence_reason": "Report publication date is June 2022; no 2023–2024 post-implementation EPR data exist in the document.",
        "gold": [],
    },
]


def save_bonus_questions() -> dict[str, Any]:
    all_questions = DEV_QUESTIONS + TEST_QUESTIONS
    BONUS_QUESTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    BONUS_QUESTIONS_PATH.write_text(json.dumps(all_questions, ensure_ascii=False, indent=2), encoding="utf-8")

    summary: dict[str, Any] = {"total": len(all_questions), "dev": {}, "test": {}}
    for q in all_questions:
        sp = q["split"]
        cat = q["category"]
        summary[sp][cat] = summary[sp].get(cat, 0) + 1
    return summary


if __name__ == "__main__":
    info = save_bonus_questions()
    print(json.dumps(info, indent=2))

