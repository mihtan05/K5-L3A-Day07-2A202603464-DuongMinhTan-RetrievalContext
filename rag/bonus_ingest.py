"""Bonus Multimodal Ingestion Pipeline for ADVANCED.md (+15 pts).

Processes the 138-page World Bank report:
  "Vietnam: Plastic Pollution Diagnostics" (June 2022, Report No. P167307, CC BY 3.0 IGO)
  Source URL: http://documents.worldbank.org/curated/en/099731406282241639/pdf/P1673071d02f2c0be180741356b6b0e3deb.pdf

Extracts and indexes 4 modalities into PostgreSQL + pgvector (strategy='BONUS'):
  1. text          : All 137 non-blank pages (Page 24 is 100% blank separator)
  2. table         : All 26 numbered tables (Table 1 - Table 26) with structured markdown + crops
  3. image_diagram : All 16 numbered informative maps, photos, device diagrams & CNN pipelines
  4. chart         : All 38 numbered quantitative charts (dual-axis, pie-of-pie, bar, line, profile)
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pymupdf

from . import day6

BONUS_STRATEGY = "BONUS"
BONUS_PDF_PATH = day6.ROOT / "data" / "bonus" / "wb_vietnam_plastic_2022.pdf"
BONUS_CROPS_DIR = day6.ROOT / "data" / "bonus" / "crops"
BONUS_CHUNKS_PATH = day6.ROOT / "data" / "bonus" / "chunks.json"
BONUS_MANIFEST_PATH = day6.ROOT / "data" / "bonus" / "index_manifest.json"
BONUS_QUESTIONS_PATH = day6.ROOT / "data" / "bonus" / "questions.json"

BONUS_SOURCE_ID = "wb_vn_plastic_2022"
BONUS_SOURCE_URL = "http://documents.worldbank.org/curated/en/099731406282241639/pdf/P1673071d02f2c0be180741356b6b0e3deb.pdf"
BONUS_SOURCE_META: dict[str, Any] = {
    "source_id": BONUS_SOURCE_ID,
    "title": "Vietnam: Plastic Pollution Diagnostics",
    "organization": "World Bank",
    "report_no": "P167307",
    "year": 2022,
    "publication_date": "2022-06-28",
    "license": "CC BY 3.0 IGO (Public Disclosure Authorized)",
    "url": BONUS_SOURCE_URL,
}


# ---------------------------------------------------------------------------
# Page-level audit (138 total pages)
# ---------------------------------------------------------------------------
BLANK_PAGES: list[dict[str, Any]] = [
    {
        "page": 24,
        "status": "skipped_blank",
        "reason": "100% blank separator page between Executive Summary and Section 1 (0 text characters, 0 embedded images).",
    }
]

DECORATIVE_PAGES: list[dict[str, Any]] = [
    {"page": 1, "status": "text_only_decorative_cover", "reason": "Front cover artwork; title/date metadata extracted, decorative cover art excluded from visual Q&A."},
    {"page": 3, "status": "text_only_decorative_title", "reason": "Inner title banner page; title extracted, decorative background excluded."},
    {"page": 12, "status": "text_only_decorative_divider", "reason": "Executive Summary section divider with blue wave graphic; heading text extracted."},
    {"page": 13, "status": "text_only_decorative_photo", "reason": "Full-page decorative background photo under Key Messages; text extracted, stock background excluded."},
    {"page": 25, "status": "text_only_decorative_divider", "reason": "Section 1 (Introduction) divider with blue wave graphic; text extracted."},
    {"page": 29, "status": "text_only_decorative_divider", "reason": "Section 2 (Main Summaries of Diagnostics Studies) divider; heading text extracted."},
    {"page": 43, "status": "text_only_decorative_photo", "reason": "Full-page decorative stock photo (Photo: Praneat - Shutterstock) with zero analytical labels; caption logged, photo excluded from visual Q&A."},
    {"page": 55, "status": "text_only_decorative_photo", "reason": "Full-page decorative stock photo (Photo: Susie Hedberg - Shutterstock); caption logged, photo excluded from visual Q&A."},
    {"page": 77, "status": "text_only_decorative_photo", "reason": "Full-page decorative stock photo (Photo: Roman Striga - Shutterstock); caption logged, photo excluded from visual Q&A."},
    {"page": 91, "status": "text_only_decorative_divider", "reason": "Section 3 (Policy Recommendations and Next Steps) divider with blue wave graphic; text extracted."},
    {"page": 94, "status": "text_only_decorative_photo", "reason": "Decorative photo banner above References; text extracted."},
    {"page": 95, "status": "text_only_decorative_photo", "reason": "Decorative photo banner on References continuation page; text extracted."},
    {"page": 101, "status": "text_only_decorative_divider", "reason": "Annexes section divider with blue wave graphic; heading text extracted."},
    {"page": 110, "status": "chart_plus_decorative_photo", "reason": "Top half contains Figure 36 (indexed chart); bottom half is a decorative stock photo (Photo: xuanhuongho - Shutterstock) excluded from visual Q&A."},
    {"page": 138, "status": "text_only_back_cover", "reason": "Back cover with World Bank logo only."},
]


# ---------------------------------------------------------------------------
# Verified Structured Table Assets (Table 1 .. Table 26)
# ---------------------------------------------------------------------------
VERIFIED_TABLES: list[dict[str, Any]] = [
    {
        "asset_id": "table_01",
        "title": "Table 1: Overview of Plastics Diagnostics Studies (Coverage and Methodologies)",
        "page": 17,
        "bbox": [0.06, 0.30, 0.94, 0.91],
        "section": "Executive Summary",
        "content": (
            "[TABLE 1 | Page 17 | Executive Summary] Table 1: Overview of the Different Methodologies Used in the Plastics Diagnostics Studies.\n"
            "- Survey of plastics on riverbanks and coastal beaches:\n"
            "  * Coverage: 38 sites: 14 coastal sites in eight locations, and 24 riverbank sites in 10 locations.\n"
            "  * Key Methodology: Standard types of litter benchmarked to international coastal clean-up categories and National Guidance, customized to Vietnam. "
            "On beaches: visual observation and collection over a 100 m beach stretch (four random 5 m transects). "
            "On riverbanks: digging down to 30 cm depth in 1 m2 quadrats. Surveys conducted once during 2020–2021.\n"
            "- Remote sensing and net trawl survey (waterways plastic transport pilot):\n"
            "  * Coverage: Nine river sites in three locations: Hai Duong, Hai Phong, and Sa Pa (Lao Cai).\n"
            "  * Key Methodology: (1) Stationary bridge cameras recording 8 hours/day per camera (24h footage per site) at 5 sites; "
            "(2) Unmanned Aerial Vehicles (UAVs/drones) at 60–100 m (high altitude) and 3–6 m (low altitude) combined with APLASTIC-Q deep-learning CNN analysis at 4 sites (9 pollution hotspots); "
            "(3) Mobile net trawls at multiple water-column depths with mechanical flow meters at 1 pilot site (Chanh Duong 2, Hai Phong).\n"
            "- Market analysis of alternatives to Top 10 single-use plastic (SUP) items:\n"
            "  * Coverage: National market (producers, importers, corporate consumers, and experts) covering 6 product categories derived from the Top 10 plastic items.\n"
            "  * Key Methodology: Primary stakeholder interviews and secondary market/customs data comparing annual units sold, wholesale costs (VND/kg or VND/unit), durability, and recyclability."
        ),
    },
    {
        "asset_id": "table_02",
        "title": "Table 2: Coastal and River Site Selection Criteria",
        "page": 31,
        "bbox": [0.07, 0.63, 0.93, 0.92],
        "section": "2.1.2.1 Survey Location and Site Selection",
        "content": (
            "[TABLE 2 | Page 31 | Section 2.1.2.1] Table 2: Coastal and River Site Selection Criteria.\n"
            "- Coastal Site Criteria:\n"
            "  1. Sandy beach or pebble shoreline.\n"
            "  2. Clear, direct, year-round access.\n"
            "  3. No breakwaters or jetties.\n"
            "  4. At least 100 meters in length, parallel to the water.\n"
            "  5. If two coastal sites are surveyed in a location: choose one beach with no regular clean-up activities (or cleaned at least 3 months prior) and one beach with regular clean-ups. If only one coastal site is included, choose either.\n"
            "- River Site Criteria:\n"
            "  1. At least 100 meters in length, parallel to the water.\n"
            "  2. Digging on the banks is possible (down to 30 cm depth in 1 m x 1 m quadrats).\n"
            "  3. Regularly flooded during the rainy season."
        ),
    },
    {
        "asset_id": "table_03",
        "title": "Table 3: Sources and 28 Plastic Sub-Categories (with Single-Use Plastic Classification)",
        "page": 32,
        "bbox": [0.07, 0.62, 0.93, 0.93],
        "section": "2.1.2.3 Waste Categorization and Brand Audit",
        "content": (
            "[TABLE 3 | Pages 32-33 | Section 2.1.2.3] Table 3: Sources and Plastic Sub-Categories (28 items across 5 sources, SUP classification).\n"
            "- i) Fisheries-related waste (items used for fishing and aquaculture):\n"
            "  * Fishing gear 1: Plastic fishing rope, net pieces, fishing lures & lines, hard plastic floats -> SUP? No\n"
            "  * Fishing gear 2: Polystyrenes-EPS, buoys & floats -> SUP? No\n"
            "  * String, plastic cords, and rope; Plastic rope -> SUP? No\n"
            "- ii) Agriculture-related waste (items used in agriculture):\n"
            "  * Fertilizer bags or containers -> SUP? No\n"
            "- iii) Take-away related waste (hospitality and tourism food packaging):\n"
            "  * Plastic bags size 1 (0–5 kg) -> SUP? Yes\n"
            "  * Plastic bags size 2 (>5 kg) -> SUP? Yes\n"
            "  * Soft plastic fragments (mostly from plastic bags) -> SUP? Yes\n"
            "  * Styrofoam food containers -> SUP? Yes\n"
            "  * Cups, utensils... (PET) -> SUP? Yes\n"
            "  * Cups, utensils... (PP) -> SUP? Yes\n"
            "  * Straws -> SUP? Yes\n"
            "- iv) Household-related waste (discarded by public inland or on coast):\n"
            "  * Hard plastic fragments (toys, kitchenware, unidentified objects) -> SUP? Yes\n"
            "  * Plastic film fragments -> SUP? Yes\n"
            "  * Crisp/Sweet packages -> SUP? Yes\n"
            "  * Food wrappers -> SUP? Yes\n"
            "  * Other wrappers (wet tissue wrappers, chopstick wrappers) -> SUP? Yes\n"
            "  * Beverage bottles (PET) size 1 (0–100 ml / 0–500 ml) & size 2 (>100 ml / >500 ml) -> SUP? Yes\n"
            "  * Other beverage bottles (HDPE), Food bottles (sauces/cooking oil), Cleaner & cosmetic bottles size 1 (0–100 ml) & size 2 (>100 ml), Bottle caps/HDPE, Cigar tips -> SUP? Yes\n"
            "  * Lighters -> SUP? No; Other plastics (slippers, sanitary products, diapers) -> SUP? No\n"
            "- v) Sanitary and medical-related waste:\n"
            "  * Personal hygiene products (toothbrushes, toothpaste tubes, razors) -> SUP? No\n"
            "  * Medical products (band-aids, medical masks, syringes) -> SUP? No"
        ),
    },
    {
        "asset_id": "table_04",
        "title": "Table 4: Clean-Coast Index (CCI) Grading Scale",
        "page": 34,
        "bbox": [0.07, 0.44, 0.93, 0.62],
        "section": "2.1.2.4 Data Analysis",
        "content": (
            "[TABLE 4 | Page 34 | Section 2.1.2.4] Table 4: Clean-Coast Index (CCI = Density of plastic items per m2 * k, where coefficient k = 20).\n"
            "| CCI Grade | Description | Numeric Index Range |\n"
            "| Very clean | No waste was seen | 0–2 |\n"
            "| Clean | No waste was seen over a large area | 2–5 |\n"
            "| Moderate | A few pieces of waste were detected | 5–10 |\n"
            "| Dirty | A lot of waste on shore/at sites | 10–20 |\n"
            "| Extremely dirty | Most of the beach/site was covered with waste | 20+ |\n"
            "Unit definition on Page 34: For river sites, 1 unit = 1 m2 x 0.3 m depth (1 m length x 1 m width x 0.3 m depth). For coastal sites, 1 unit = 1 m2 (1 m long x 1 m wide)."
        ),
    },
    {
        "asset_id": "table_05",
        "title": "Table 5: List of 38 Survey Sites Across 10 Locations in Vietnam",
        "page": 37,
        "bbox": [0.07, 0.08, 0.93, 0.92],
        "section": "2.1.3.1 Overview of Survey Sites",
        "content": (
            "[TABLE 5 | Pages 37-38 | Section 2.1.3.1] Table 5: List of 38 Survey Sites (Location, Site Name, River System/Subzone, Site Type, Rural R vs Urban U, Tourism T vs Non-tourism NT, Survey Date).\n"
            "- Lao Cai Province (July 2020, Red River, all 4 River sites): 1. Ngoi Dum (River, U, NT); 2. Muong Hoa (River, R, T); 3. Ta Van (River, R, T); 4. Ngoi Duong (River, U, NT).\n"
            "- Hai Phong City (September 2020, 2 Coastal + 2 River): 5. Do Son (Northern Coastal, U, T); 6. Cat Hai (Northern Coastal, U, T); 7. Lach Tray (Red River, U, NT); 8. Van Uc (Red River, R, NT).\n"
            "- Hue City (November 2020, 1 Coastal + 2 River): 9. Thuan An (Northern Coastal, U, T); 10. Huong (Central rivers, River, U, T); 11. Bo (Central rivers, River, R, NT).\n"
            "- Da Nang (November 2020, 2 Coastal + 2 River): 12. Bien Dong (Transitional Coastal, U, T); 13. Nam O (Transitional Coastal, U, T); 14. Cu De upstream (Central rivers, River, R, NT); 15. Cu De downstream (Central rivers, River, U, NT).\n"
            "- Quang Nam (November 2020, 1 Coastal + 2 River): 16. Rang (Transitional Coastal, R, T); 17. Tam Ky (Central rivers, River, U, NT); 18. Truong Giang (Central rivers, River, U, T).\n"
            "- Khanh Hoa (November 2020 & January 2021, 3 Coastal + 3 River): 19. Vinh Nguyen (Transitional Coastal, U, T, Nov 2020); 20. Quang Truong middle-class area (Central rivers, River, U, NT, Nov 2020); 21. Quang Truong downstream area (Central rivers, River, U, T, Nov 2020); 22. My Ca (Transitional Coastal, U, NT, Jan 2021); 23. Binh Lap (Transitional Coastal, R, NT, Jan 2021); 24. Can (Central rivers, River, R, NT, Jan 2021).\n"
            "- Ho Chi Minh City (October 2020, 1 Coastal + 2 River): 25. April 30 (Southern Coastal, R, T); 26. Sai Gon (Dong Nai-Sai Gon River, U, NT); 27. Dong Nai (Dong Nai-Sai Gon River, R, T).\n"
            "- Soc Trang Province (October 2020, 2 Coastal + 2 River): 28. Lai Hoa (Southern Coastal, R, NT); 29. Ho Be (Southern Coastal, R, NT); 30. Long Phu (Mekong River, U, NT); 31. My Thanh (Mekong River, R, NT).\n"
            "- Can Tho City (October 2020, all 3 River sites): 32. 3/2 (Mekong River, U, NT); 33. Rau Ram (Mekong River, U, NT); 34. Cai Khe (Mekong River, U, NT).\n"
            "- Phu Quoc Island (October 2020, 2 Coastal + 2 River): 35. Sao (Southern Coastal, U, T); 36. Truong (Southern Coastal, U, NT); 37. Cua Can (Phu Quoc River, R, NT); 38. Duong Dong (Phu Quoc River, U, T).\n"
            "Summary totals from Table 5: 38 total sites = 14 Coastal sites + 24 River sites; 15 Rural (R) sites + 23 Urban (U) sites; 16 Tourism (T) sites + 22 Non-tourism (NT) sites."
        ),
    },
    {
        "asset_id": "table_06",
        "title": "Table 6: Clean-Coast Index (CCI) at the 14 Coastal Sites in Vietnam",
        "page": 52,
        "bbox": [0.07, 0.08, 0.93, 0.56],
        "section": "2.1.3.4 Results of the Survey Conducted at Coastal Sites",
        "content": (
            "[TABLE 6 | Page 52 | Section 2.1.3.4] Table 6: Clean-Coast Index (CCI) at the 14 Coastal Sites.\n"
            "| No | Location | Site Name | Density (item/m2) | Weight (g/m2) | CCI | Rating |\n"
            "| 1 | Hai Phong | Do Son | 0.46 | 4.61 | 9.28 | Moderate |\n"
            "| 2 | Hai Phong | Cat Hai | 4.30 | 17.6 | 85.9 | Extremely Dirty |\n"
            "| 3 | Thua Thien Hue | Thuan An | 2.66 | 14.3 | 53.3 | Extremely Dirty |\n"
            "| 4 | Da Nang | Bien Dong | 0.91 | 2.09 | 18.2 | Dirty |\n"
            "| 5 | Da Nang | Nam O | 0.89 | 6.86 | 17.7 | Dirty |\n"
            "| 6 | Quang Nam | Rang | 5.23 | 34.2 | 104.5 | Extremely Dirty |\n"
            "| 7 | Nha Trang (Khanh Hoa) | Vinh Nguyen | 1.63 | 9.33 | 32.6 | Extremely Dirty |\n"
            "| 8 | Nha Trang (Khanh Hoa) | My Ca | 1.54 | 8.95 | 30.8 | Extremely Dirty |\n"
            "| 9 | Nha Trang (Khanh Hoa) | Binh Lap | 18.9 | 76.7 | 379.8 | Extremely Dirty |\n"
            "| 10 | Ho Chi Minh | 30/4 (April 30) | 3.74 | 25.1 | 74.9 | Extremely Dirty |\n"
            "| 11 | Soc Trang | Lai Hoa | 3.43 | 22.8 | 68.5 | Extremely Dirty |\n"
            "| 12 | Soc Trang | Ho Be | 0.39 | 3.63 | 7.80 | Moderate |\n"
            "| 13 | Phu Quoc | Bai Sao | 1.32 | 9.69 | 26.4 | Extremely Dirty |\n"
            "| 14 | Phu Quoc | Bai Truong | 2.57 | 13.7 | 51.3 | Extremely Dirty |\n"
            "Summary: Out of 14 coastal sites, 10 sites (71.4%) were 'Extremely Dirty' (CCI > 20), 2 sites (14.3%: Bien Dong 18.2 and Nam O 17.7 in Da Nang) were 'Dirty' (CCI 10–20), and 2 sites (14.3%: Do Son 9.28 in Hai Phong and Ho Be 7.80 in Soc Trang) were 'Moderate' (CCI 5–10). Highest CCI: Binh Lap (379.8, density 18.9 items/m2, weight 76.7 g/m2). Lowest CCI: Ho Be (7.80, density 0.39 items/m2, weight 3.63 g/m2)."
        ),
    },
    {
        "asset_id": "table_07",
        "title": "Table 7: Top 10 Plastic Waste Items Found at River and Coastal Sites (Percentage by Number)",
        "page": 54,
        "bbox": [0.07, 0.08, 0.93, 0.62],
        "section": "2.1.4 Discussion and Conclusions",
        "content": (
            "[TABLE 7 | Page 54 | Section 2.1.4] Table 7: Top 10 Plastic Waste Items Found at River and Coastal Sites (Percentage by Number).\n"
            "| Rank | River Sites (Item & % by number) | Coastal Sites (Item & % by number) |\n"
            "| 1 | Plastic bags size 1 (0–5 kg): 21.9% | Fishing gear 1 (Plastic rope, net pieces, lures, lines, floats): 18.5% |\n"
            "| 2 | Styrofoam food containers: 11.4% | Soft plastic fragments: 18.1% |\n"
            "| 3 | Soft plastic fragments: 10.8% | Fishing gear 2 (Polystyrenes-EPS, buoys, floats): 14.0% |\n"
            "| 4 | Other food wrappers: 8.8% | Plastic bags size 1 (0–5 kg): 7.1% |\n"
            "| 5 | Crisp/sweet packaging: 5.8% | Styrofoam food containers: 6.8% |\n"
            "| 6 | String, plastic cords and ropes: 5.7% | Hard plastic fragments: 6.4% |\n"
            "| 7 | Other plastics (slippers, diapers, etc.): 4.7% | Straws: 4.9% |\n"
            "| 8 | Hard plastic fragments: 4.6% | Other plastics: 2.8% |\n"
            "| 9 | Other wrappers (wet tissues, chopsticks): 4.1% | Crisp/sweet packages: 2.8% |\n"
            "| 10 | Fishing gear 2 (Polystyrenes-EPS, buoys, floats): 3.5% | Other food wrappers: 2.6% |\n"
            "| Total Top 10 | 81.3% (River sites) | 84.0% (Coastal sites) |"
        ),
    },
    {
        "asset_id": "table_08",
        "title": "Table 8: Location and Site Selection Criteria and Information on Selected Study Locations (Hai Phong, Lao Cai/Sapa, Hai Duong)",
        "page": 57,
        "bbox": [0.07, 0.08, 0.93, 0.88],
        "section": "2.2.2 Selection of Study Locations",
        "content": (
            "[TABLE 8 | Page 57 | Section 2.2.2] Table 8: Location and Site Selection Criteria for Remote Sensing & River Transport Study.\n"
            "| Criteria | 1. Hai Phong City | 2. Lao Cai / Sapa | 3. Hai Duong Province |\n"
            "| Population level (impacted population) | 2 million people | Lao Cai city — 25% of province's population (173,840) | About 2 million people |\n"
            "| Environmental impact (location type) | Urban, coastal, river location | Urban, river upstream | Urban, river location |\n"
            "| Waste treatment facilities | 6–8 treatment facilities (one new); landfills | One treatment facility; landfills | Two treatment facilities; landfills |\n"
            "| Waste collection rate | 90% | 85% | 80–85% |\n"
            "| Critical ecosystem protection proximity | Biosphere Reserve (Cat Ba Island) | Hoang Lien National Park | x (None listed) |\n"
            "| Potential for blocking waterways / flooding / health impacts | High impact potential | High impact potential | High impact potential |\n"
            "| Economic impact: Tourism share | Significant tourism, including adjacent Cat Ba Island | Significant rural and community tourism | High priority heritage tourism site |\n"
            "| Economic impact: Fisheries & aquaculture revenue | Medium fisheries and coastal aquaculture impact | Low fisheries and aquaculture impacts | Low fisheries and aquaculture impacts |"
        ),
    },
    {
        "asset_id": "table_09",
        "title": "Table 9: Survey Sites' Coordinates (Remote Sensing and River Monitoring Study)",
        "page": 59,
        "bbox": [0.07, 0.14, 0.93, 0.52],
        "section": "2.2.2 Selection of Study Locations",
        "content": (
            "[TABLE 9 | Page 59 | Section 2.2.2] Table 9: Survey Sites' Coordinates (9 River Transport Monitoring Sites).\n"
            "| ID | Survey Site | Location | Latitude | Longitude |\n"
            "| 1 | Chanh Duong 1 | Vinh Bao - Hai Phong | 20.639106 | 106.582464 |\n"
            "| 2 | Chanh Duong 2 | Vinh Bao - Hai Phong | 20.641278 | 106.566986 |\n"
            "| 3 | Dang bridge | Tien Lang - Hai Phong | 20.677672 | 106.551364 |\n"
            "| 4 | Thach Khoi 1 | Hai Duong | 20.882731 | 106.296247 |\n"
            "| 5 | Thach Khoi 2 | Hai Duong | 20.818602 | 106.282264 |\n"
            "| 6 | Han bridge | Hai Duong | 20.958615 | 106.309602 |\n"
            "| 7 | Suoi Cat 1 | Sa Pa - Lao Cai | 22.3052 | 103.889653 |\n"
            "| 8 | Suoi Cat 2 | Sa Pa - Lao Cai | 22.309917 | 103.875822 |\n"
            "| 9 | Suoi Cat 3 | Sa Pa - Lao Cai | 22.310181 | 103.86015 |"
        ),
    },
    {
        "asset_id": "table_10",
        "title": "Table 10: Data Analysis Carried Out by Survey Site (Drone, Bridge Cameras, Net Sampling)",
        "page": 61,
        "bbox": [0.07, 0.42, 0.93, 0.88],
        "section": "2.2.2 Selection of Study Locations",
        "content": (
            "[TABLE 10 | Page 61 | Section 2.2.2] Table 10: Data Analysis Carried Out by Survey Site.\n"
            "| ID | Survey Site | Location | Waste Quantities (drone) | Waste Types (drone) | Transport (bridge cameras) | Waste Types (net sampling) |\n"
            "| 1 | Chanh Duong 1 | Vinh Bao - Hai Phong | Y | Y | Y | - |\n"
            "| 2 | Chanh Duong 2 | Vinh Bao - Hai Phong | Y | Y | Y* (two camera surveys) | Y |\n"
            "| 3 | Dang bridge | Tien Lang - Hai Phong | - | - | Y | - |\n"
            "| 4 | Thach Khoi 1 | Hai Duong | Y | Y | - | - |\n"
            "| 5 | Thach Khoi 2 | Hai Duong | - | - | Y | - |\n"
            "| 6 | Han bridge | Hai Duong | - | - | - | - |\n"
            "| 7 | Suoi Cat 1 | Sa Pa - Lao Cai | Y | Y | - | - |\n"
            "| 8 | Suoi Cat 2 | Sa Pa - Lao Cai | - | - | Y | - |\n"
            "| 9 | Suoi Cat 3 | Sa Pa - Lao Cai | - | - | - | - |\n"
            "Summary: Only Chanh Duong 2 (ID 2, Vinh Bao - Hai Phong) had all four analyses (Drone Quantities, Drone Types, Bridge Camera Transport with 2 camera surveys, and Net Sampling). Han bridge (ID 6) and Suoi Cat 3 (ID 9) had no completed data analysis."
        ),
    },
    {
        "asset_id": "table_11",
        "title": "Table 11: Waste Quantities, Areas, and Volumes for 9 Pollution Hotspots (Drone Surveys)",
        "page": 65,
        "bbox": [0.07, 0.34, 0.93, 0.77],
        "section": "2.2.4.1 Results of the Drone Surveys",
        "content": (
            "[TABLE 11 | Page 65 | Section 2.2.4.1] Table 11: Waste Quantities, Areas, and Volumes for Pollution Hotspots at Thach Khoi 1, Chanh Duong 1 & 2, and Suoi Cat 1.\n"
            "| Pollution Hotspot | Assessed Waste Items | Waste Area (m2) | Volume Area (m3) | Corrected Waste Item Numbers (for sites with little pollution) |\n"
            "| Hai Duong, Thach Khoi 1, site 1 | 2,986 | 25 | 6 | (not applicable / heavily polluted) |\n"
            "| Hai Duong, Thach Khoi 1, site 2 | 2,521 | 20 | 5 | (not applicable / heavily polluted) |\n"
            "| Hai Phong, Chanh Duong 01, Site 1 | 192 | 1 | 0 | 101.5 |\n"
            "| Hai Phong, Chanh Duong 01, Site 2 | 66 | 0 | 0 | 39.4 |\n"
            "| Hai Phong, Chanh Duong 01, Site 3 | 103 | 0 | 0 | 60 |\n"
            "| Hai Phong, Chanh Duong 02, site 1 | 214 | 1 | 0 | 82.4 |\n"
            "| Hai Phong, Chanh Duong 02, site 2 | 163 | 1 | 0 | 51.5 |\n"
            "| Suoi Cat 01_1 (Sapa) | 857 | 1 | 0 | 296 |\n"
            "| Suoi Cat 01_2 (Sapa) | 378 | 0 | 0 | 116 |\n"
            "Totals & notes: Thach Khoi 1 (sites 1 + 2) had 2,986 + 2,521 = 5,507 assessed waste items covering 25 + 20 = 45 m2 and 6 + 5 = 11 m3 volume. "
            "The 5 Hai Phong hotspots had 192+66+103+214+163 = 738 assessed items, or 101.5+39.4+60+82.4+51.5 = 334.8 corrected items across 3 m2. "
            "Suoi Cat 1 (sites 1 + 2) had 857 + 378 = 1,235 assessed items, or 296 + 116 = 412 corrected items."
        ),
    },
    {
        "asset_id": "table_12",
        "title": "Table 12: Detailed Proportional Waste Types, Totals, and Locations (Drone Surveys)",
        "page": 68,
        "bbox": [0.07, 0.08, 0.93, 0.72],
        "section": "2.2.4.1 Results of the Drone Surveys",
        "content": (
            "[TABLE 12 | Page 68 | Section 2.2.4.1] Table 12: Detailed Proportional Waste Types, Totals, and Locations (APLASTIC-Q Drone Analysis).\n"
            "| Waste Type | All Sites (Items) | All Sites (%) | Hai Duong (%) | Hai Phong (%) | Sapa (%) |\n"
            "| Bags LDPE thick | 14 | 0% | 0% | 3% | 3% |\n"
            "| Bags LDPE | 287 | 6% | 3% | 23% | 13% |\n"
            "| Bags robust PET | 233 | 5% | 5% | 5% | 6% |\n"
            "| Wrappers under 10cm | 164 | 4% | 4% | 2% | 0% |\n"
            "| Wrappers over 10cm | 121 | 3% | 3% | 2% | 1% |\n"
            "| Bottles PET | 256 | 6% | 5% | 7% | 11% |\n"
            "| Polystyrene under 20cm (incl. food containers) | 1,735 | 38% | 40% | 28% | 18% |\n"
            "| Polystyrene over 20cm | 123 | 3% | 3% | 2% | 0% |\n"
            "| PPCP bottle / medical / other | 0 | 0% | 0% | 0% | 0% |\n"
            "| Fishing gear | 6 | 0% | 0% | 0% | 1% |\n"
            "| Cup lids, caps and small plastics | 886 | 19% | 21% | 4% | 18% |\n"
            "| Other plastics over 20cm | 204 | 4% | 4% | 4% | 6% |\n"
            "| Rubber | 6 | 0% | 0% | 0% | 1% |\n"
            "| Metal | 3 | 0% | 0% | 0% | 0% |\n"
            "| Glass | 0 | 0% | 0% | 0% | 0% |\n"
            "| Other non-plastics | 580 | 13% | 12% | 20% | 19% |\n"
            "Total items across all sites = 4,618 items. Note: Combined Polystyrene (under 20cm 38% + over 20cm 3% = 40% rounded, 1,858 items) is the #1 category overall and in Hai Duong (43%) and Hai Phong (30%)."
        ),
    },
    {
        "asset_id": "table_13",
        "title": "Table 13: Plastics River Monitoring Results for Hai Duong, Hai Phong, and Sapa (Bridge Cameras)",
        "page": 69,
        "bbox": [0.07, 0.08, 0.93, 0.91],
        "section": "2.2.4.2 Bridge Camera Results",
        "content": (
            "[TABLE 13 | Page 69 | Section 2.2.4.2] Table 13: Plastics River Monitoring Results (Half-hourly floating plastic item counts from 0h to 9h across 5 bridges; extrapolated to 600m river width in parentheses).\n"
            "| Time Interval | Hai Duong, Thach Khoi 2 | Hai Phong, Chanh Duong 01 | Hai Phong, Chanh Duong 02 | Hai Phong, Dang bridge | Sapa, Suoi Cat 2 |\n"
            "| 0h - 0.5h | 17 | 4 (8) | 35 (45) | 0 | 20 |\n"
            "| 0.5h - 1h | 15 | 6 (13) | 36 (46) | 0 | 20 |\n"
            "| 1h - 1.5h | 22 | 5 (10) | 28 (36) | 3 | 12 |\n"
            "| 1.5h - 2h | 11 | 22 (46) | 21 (27) | 10 | 25 |\n"
            "| 2h - 2.5h | 16 | 17 (36) | 37 (48) | 10 | 25 |\n"
            "| 2.5h - 3h | 16 | 24 (50) | 51 (66) | 41 | 30 |\n"
            "| 3h - 3.5h | 24 | 25 (52) | 23 (30) | 14 | 15 |\n"
            "| 3.5h - 4h | 12 | 25 (52) | 34 (44) | 9 | 20 |\n"
            "| 4h - 4.5h | 9 | 31 (65) | 28 (36) | 9 | 25 |\n"
            "| 4.5h - 5h | 5 | 25 (52) | 21 (27) | 6 | 18 |\n"
            "| 5h - 5.5h | 12 | 12 (25) | 23 (30) | 10 | 25 |\n"
            "| 5.5h - 6h | 18 | 19 (40) | 42 (54) | 21 | 25 |\n"
            "| 6h - 6.5h | 2 | 14 (29) | 32 (41) | 4 | 17 |\n"
            "| 6.5h - 7h | 17 | 23 (48) | 24 (31) | 2 | 15 |\n"
            "| 7h - 7.5h | 11 | 19 (40) | 19 (25) | 0 | 18 |\n"
            "| 7.5h - 8h | 10 | 8 (17) | 8 (10) | 1 | 21 |\n"
            "| 8h - 8.5h | 11 | 7 (15) | 1 (1) | - | 29 |\n"
            "| 8.5h - 9h | 8 | - | - | - | - |\n"
            "| SUM (Total items) | 236 | 286 (600) | 465 (600) | 140 | 360 |"
        ),
    },
    {
        "asset_id": "table_14",
        "title": "Table 14: Number and Weight of Waste Types Collected During Net Sampling at Chanh Duong 2",
        "page": 72,
        "bbox": [0.07, 0.08, 0.93, 0.91],
        "section": "2.2.4.3 Net Sampling Results",
        "content": (
            "[TABLE 14 | Page 72 | Section 2.2.4.3] Table 14: Number and Weight of Waste Types Collected During Net Sampling (Chanh Duong 2 Bridge, Hai Phong, 3 vertical positions x 2 depths, 2-hour deployment each).\n"
            "- POS 01 (9h40 - 11h40):\n"
            "  * Upper net: Beverage bottle (3 pcs, 35 g), Plastic bag (12 pcs, 48 g), Single-use plastic cups/utensils (1 pc, 20 g), Other plastic (5 pcs, 8 g), Organic waste (425 g).\n"
            "  * Lower net: Plastic bag (6 pcs, 15 g), Packages & other wrapper (14 pcs, 15 g), Organic waste (275 g).\n"
            "- POS 02 (8h30 - 10h30):\n"
            "  * Upper net: Straws (2 pcs, 0 g), Bottle cap (1 pc, 0 g), Plastic bag (5 pcs, 65 g), Single-use plastic cups/utensils (1 pc, 5 g), Packages & other wrapper (8 pcs, 10 g), Other plastic (3 pcs, 65 g), Organic waste (145 g).\n"
            "  * Lower net: Plastic bag (5 pcs, 70 g), Packages & other wrapper (9 pcs, 10 g), Other plastic (3 pcs, 5 g), Organic waste (335 g).\n"
            "- POS 03 (13h20 - 15h20):\n"
            "  * Upper net: Bottle cap (2 pcs, 0 g), Plastic bag (4 pcs, 20 g), Single-use plastic cups/utensils (2 pcs, 10 g), Packages & other wrapper (6 pcs, 12 g), Other plastic (10 pcs, 490 g), Organic waste (65 g).\n"
            "  * Lower net: Plastic bag (5 pcs, 165 g), Packages & other wrapper (13 pcs, 25 g), Other plastic (1 pc, 3 g), Organic waste (255 g).\n"
            "- SUM across all positions (Total = 121 plastic pieces, total weight = 2,586 g including 1,500 g organic waste and 1,086 g plastic):\n"
            "  * Packages and other wrapper: 50 pieces (41.32% of quantity), 72 g (2.78% of total weight)\n"
            "  * Plastic bag: 37 pieces (30.58% of quantity), 383 g (14.81% of total weight)\n"
            "  * Other plastic: 22 pieces (18.18% of quantity), 571 g (22.08% of total weight)\n"
            "  * Single-use plastic product (cups, utensils): 4 pieces (3.31% of quantity), 35 g (1.35% of total weight)\n"
            "  * Beverage bottle: 3 pieces (2.48% of quantity), 35 g (1.35% of total weight)\n"
            "  * Bottle cap: 3 pieces (2.48% of quantity), 0 g\n"
            "  * Straws: 2 pieces (1.65% of quantity), 0 g\n"
            "  * Organic waste: uncounted quantity (decomposing/fragmented), 1,500 g (58.0% of total weight)."
        ),
    },
    {
        "asset_id": "table_15",
        "title": "Table 15: Top 10 Plastic Waste Items at River and Coastal Sites in Vietnam (for Alternatives Analysis)",
        "page": 78,
        "bbox": [0.07, 0.44, 0.93, 0.88],
        "section": "2.3.2 Study Design, Data Sources, and Limitations",
        "content": (
            "[TABLE 15 | Page 78 | Section 2.3.2] Table 15: Top 10 Plastic Waste Items at River and Coastal Sites in Vietnam (Combined Survey % by Number and Polymer Types).\n"
            "| Rank | Top 10 Plastic Waste Items (and Polymer) | Share (%) |\n"
            "| 1 | Soft plastic fragments (LDPE) | 17.4% |\n"
            "| 2 | Fishing gear 1: rope, net pieces, lures, lines, hard plastic floats (PE & PP) | 16.6% |\n"
            "| 3 | Fishing gear 2: Polystyrenes-ESP, buoys, floats (PS & EPS) | 13.0% |\n"
            "| 4 | Plastic bags size 1 (0–5 kg) | 8.4% |\n"
            "| 5 | Styrofoam food containers (PS) | 7.4% |\n"
            "| 6 | Hard plastic fragments (HDPE) | 6.1% |\n"
            "| 7 | Straws (mainly PP) | 4.6% |\n"
            "| 8 | Other food wrappers | 3.2% |\n"
            "| 9 | Other plastic (plastic slippers, diapers, etc.) | 3.2% |\n"
            "| 10 | Crisp/Sweet packages (PP & PS) | 3.1% |"
        ),
    },
    {
        "asset_id": "table_16",
        "title": "Table 16: Six Product Type Categories for Market Alternatives Analysis",
        "page": 79,
        "bbox": [0.07, 0.46, 0.93, 0.76],
        "section": "2.3.2 Study Design, Data Sources, and Limitations",
        "content": (
            "[TABLE 16 | Page 79 | Section 2.3.2] Table 16: Categories for Market Alternatives Analysis (Mapping 6 Product Categories to Top 10 Waste Items; Hard plastic fragments #6 and Other plastics #9 excluded as too heterogeneous).\n"
            "| Product Type Category for Alternatives Analysis | Corresponding Top 10 Plastic Waste Items |\n"
            "| 1. Plastic bags (different sizes) | Plastic bags size 1 (0–5 kg) + Soft plastic fragments (LDPE) |\n"
            "| 2. Fishing nets | Fishing gear 1: Plastic rope, net pieces, lures, lines, hard plastic floats (PE & PP) |\n"
            "| 3. Various foam floats | Fishing gear 2: Polystyrenes-ESP, buoys, floats (PS & EPS) |\n"
            "| 4. Styrofoam food containers | Styrofoam food containers (PS) |\n"
            "| 5. Straws | Straws (mainly PP) |\n"
            "| 6. Food packaging | Other food wrappers + Crisp/Sweet packages (PP & PS) |"
        ),
    },
    {
        "asset_id": "table_17",
        "title": "Table 17: Plastic Bags and Alternatives – Units Sold and Wholesale Costs",
        "page": 81,
        "bbox": [0.07, 0.46, 0.93, 0.92],
        "section": "2.3.3 Key Findings (Plastic Bags)",
        "content": (
            "[TABLE 17 | Pages 81-82 | Section 2.3.3] Table 17: Plastic Bags and Alternatives – Units Sold per Year and Average Wholesale Costs.\n"
            "- Plastic Bag Types:\n"
            "  * PE bag (various sizes): 284,692 tons/year | 30,000–40,000 VND/kg\n"
            "  * HDPE plastic bag (various sizes): 360,000 tons/year | 36,000–48,000 VND/kg\n"
            "  * Cup-bag (various sizes): 1,584 tons/year | 42,000–60,000 VND/kg\n"
            "  * Milktea cup-bag (various sizes): 1,408 tons/year | 30,000–48,000 VND/kg\n"
            "- Alternative Bag Types:\n"
            "  * Compostable plastic bag (various sizes): 51,897 tons/year | 160,000 VND/kg (single-use)\n"
            "  * PP woven bag: 86,400 tons/year | 19,000–25,000 VND/pcs (use for 1–2 years)\n"
            "  * Non-woven bag: 1,728 tons/year | 8,000–15,000–30,000 VND/pcs (use for 1–3 years)\n"
            "  * Wooden bag: N/A tons | 61,000–125,000 VND/pcs (use for 1–3 years)\n"
            "  * Ivory paper bag: 20,976 tons/year | 2,000–20,000 VND/pcs (use for 3–10 times)\n"
            "  * Flat Non-woven Fabric Bag: N/A | 6,000–6,500 VND/pcs (use for at least 5–10 times)\n"
            "  * Kraft paper bag: N/A | 1,000–9,000 VND/pcs (use for 1–3 times)\n"
            "  * Canvas bag for cup: N/A | 6,000–10,000 VND/pcs (use for at least 1 year)\n"
            "  * T-shaped kraft paper bag for cup: 16 tons/year | 700–1,000 VND/pcs (single-use)\n"
            "  * Compostable plastic cup-bag: N/A | 160,000 VND/kg (single-use)"
        ),
    },
    {
        "asset_id": "table_18",
        "title": "Table 18: Fishing Nets and Alternatives – Units Sold and Wholesale Costs",
        "page": 84,
        "bbox": [0.07, 0.14, 0.93, 0.58],
        "section": "2.3.3 Key Findings (Fishing Nets)",
        "content": (
            "[TABLE 18 | Page 84 | Section 2.3.3] Table 18: Fishing Nets and Alternatives – Units Sold and Wholesale Costs.\n"
            "- Parachute fishing net (mesh size 1.5 cm–40 cm): 45,054 tons/year | 20,800–25,000 VND/m2 (durability of 4–6 years) vs. Biodegradable net: N/A units sold | 70,000–138,000 VND/m2 (decomposes after 6 months in water).\n"
            "- Traditional fishing net (mesh size 2 cm–12 cm): 29,212 tons/year | 2,160–7,630 VND/m2 (durability of 6 months to 3 years) vs. Coir net (coconut fiber): N/A units sold | 22,000–25,000 VND/m2 (durability of 1–2 years).\n"
            "- Aquaculture net (mesh size 0.2 cm–5 cm): 14,500 tons/year | 3,000–15,000 VND/m2 (durability of 2–5 years) vs. Metal wire net: N/A units sold | 32,000–100,000 VND/m2 (durability of 3–5 years)."
        ),
    },
    {
        "asset_id": "table_19",
        "title": "Table 19: Various Foam Floats and Alternatives – Units Sold and Wholesale Costs",
        "page": 85,
        "bbox": [0.07, 0.14, 0.93, 0.62],
        "section": "2.3.3 Key Findings (Foam Floats)",
        "content": (
            "[TABLE 19 | Page 85 | Section 2.3.3] Table 19: Various Foam Floats and Alternatives – Units Sold and Wholesale Costs.\n"
            "- Styrofoam floats for fishing nets: 1,452 tons/year | 500–100,000 VND/unit (lasts 2–3 years) vs. Hard-plastic (HDPE) floats: 5,220 tons/year | 2,000–200,000 VND/unit (lasts 5–10 years).\n"
            "- Styrofoam floats for floating cages/rafts (aquaculture): 16,800 tons/year | 380,000–550,000 VND/unit (lasts 1–2 years) vs. Composite/HDPE floats for cages: 1,500 tons/year | 900,000–1,450,000 VND/unit (lasts 10–15 years), Metal drums: 200,000–350,000 VND/unit (lasts 1–2 years), and Bamboo rafts: 70,000–100,000 VND/tree (lasts 1–2 years)."
        ),
    },
    {
        "asset_id": "table_20",
        "title": "Table 20: Styrofoam Trays and Alternatives – Units Sold and Wholesale Costs",
        "page": 86,
        "bbox": [0.07, 0.44, 0.93, 0.92],
        "section": "2.3.3 Key Findings (Styrofoam Food Containers)",
        "content": (
            "[TABLE 20 | Pages 86-87 | Section 2.3.3] Table 20: Styrofoam Trays/Food Boxes and Alternatives – Units Sold and Wholesale Costs.\n"
            "- Styrofoam trays (for fresh food packaging): 25,650 tons/year (approx. 5,700 million pcs) | 180–450 VND/unit.\n"
            "  * Alternatives to trays: Compostable tray (PLA/PBAT): 2,200 VND/unit (single-use); Bagasse (sugarcane) tray: 1,200–2,200 VND/unit (single-use); Kraft paper tray: 1,206 million pcs/year | 2,800 VND/unit (single-use).\n"
            "- Foam food boxes (for take-away meals): 38,000 tons/year | 473–546 VND/unit (standard) up to 2,760 VND/unit.\n"
            "  * Alternatives to foam food boxes: Paper rice box: 5,700–6,900 VND/unit (single-use); Glass box: 99,000–180,000 VND/unit (reusable); Aluminum box: 5,000 VND/unit (single-use); Bagasse rice box: 2,300–5,500 VND/unit (single-use)."
        ),
    },
    {
        "asset_id": "table_21",
        "title": "Table 21: Plastic Straws and Alternatives – Units Sold and Wholesale Costs",
        "page": 88,
        "bbox": [0.07, 0.24, 0.93, 0.88],
        "section": "2.3.3 Key Findings (Straws)",
        "content": (
            "[TABLE 21 | Page 88 | Section 2.3.3] Table 21: Plastic Straws and Alternatives – Units Sold and Wholesale Costs.\n"
            "| Straw Type | Units Sold/Year | Wholesale Cost | Alternative Product Type | Units Sold/Year | Wholesale Cost & Lifespan |\n"
            "| Straight straw (PP plastic) | 1,257 million pcs | 200–1,000 VND/unit | Bamboo/wooden straw | 65 million pcs | 600–1,000 VND/unit wholesale (1,000–6,000 VND retail, use 3–6 months) |\n"
            "| Straight straw (PP plastic) | - | - | Paper/kraft straw | 850 million pcs | 200–500 VND/unit (single-use) |\n"
            "| Straight straw (PP plastic) | - | - | Grass straw | 85 million pcs | 400–500 VND/unit (single-use) |\n"
            "| Straight straw (PP plastic) | - | - | Compostable plastic straw | N/A | 3,200–3,800 VND/unit (single-use) |\n"
            "| Straight straw (PP plastic) | - | - | Rice straw / vegetable straws | 580 million pcs | 300–800 VND/unit (single-use) |\n"
            "| U-shaped straws for dairy factories (PP plastic) | 2,560 million pcs | 100–300 VND/unit | U-shaped paper straw / sugar cane fibers | 680 million pcs | 400 VND/unit (single-use) |\n"
            "Totals: Conventional PP plastic straws = 1,257 + 2,560 = 3,817 million pcs/year. Quantified alternative straws = 65 + 850 + 85 + 580 + 680 = 2,260 million pcs/year."
        ),
    },
    {
        "asset_id": "table_22",
        "title": "Table 22: Survey Site Characterization Sheet Template",
        "page": 102,
        "bbox": [0.07, 0.14, 0.93, 0.90],
        "section": "Annex 2.1.A: Survey Data Sheet Templates",
        "content": (
            "[TABLE 22 | Pages 102-103 | Annex 2.1.A] Table 22: Survey Site Characterization Sheet Template.\n"
            "Fields recorded before each beach/river survey: Organization, Surveyor name, Phone number, Date, Shoreline code (ID), Shoreline name, Location (Ward, District, Province), Time start/end, "
            "Coordinates of start and end of shoreline site (Longitude, Latitude; recorded in both corners if width > 6 m), Photo ID, Width of beach (100 m), Substratum type (Sand, Gravel, Coral), "
            "Substrate uniformity (% coverage of main substrate), Tidal range (Max & Min vertical tidal range in feet), Back of shoreline description, Major land use, Access type (vehicular/pedestrian/boat), "
            "Nearest town distance, Nearest river/stream outlet distance, and Clean-up frequency."
        ),
    },
    {
        "asset_id": "table_23",
        "title": "Table 23: Field Survey Data Sheet Template (7 Material Categories and 25+ Plastic Item Codes)",
        "page": 104,
        "bbox": [0.07, 0.12, 0.93, 0.91],
        "section": "Annex 2.1.A: Survey Data Sheet Templates",
        "content": (
            "[TABLE 23 | Pages 104-105 | Annex 2.1.A] Table 23: Field Survey Data Sheet Template.\n"
            "Header fields: Survey site name, ID transect, Time (Start/End), Date (dd/mm/yy), Length of transect (m), Width of transect (m).\n"
            "Categories recorded by Number and Weight:\n"
            "- P (PLASTIC): 1. Hard plastic fragments; 2. Soft plastic fragments; 3. Film plastic fragments; 4. Crisp/Sweet packages; 5. Food wrappers; 6. Other wrappers; "
            "7. Beverage bottles (PET) Size 1 (0–500 ml) & Size 2 (>500 ml); 8. Other Beverage bottles (HDPE); 9. Containers and bottles; "
            "10. Cleaner and cosmetics bottles Size 1 (0–100 ml) & Size 2 (>100 ml); 11. Bottle caps (HDPE); 12. Cigar/Cigarette butts; "
            "13. Plastic bags Size 1 (0–5 kg) & Size 2 (>5 kg); 14. Styrofoam food containers; 15. Single-use plastic products (Cups, Utensils - PET); "
            "16. Single-use plastic products (Cups, Utensils - PP); 17. Straws; 18. Fertilizer bags or containers; 19. Plastic strings, cords and ropes; "
            "20. Personal hygiene products; 21. Medical products; 22. Fishing gear 1 (plastic ropes, net pieces, lures, lines, hard floats); "
            "23. Fishing gear 2 (Polystyrenes-ESP, buoys & floats); 24. Other plastic; 25. Lighters.\n"
            "- Non-plastic categories: M (METAL), G (GLASS), R (RUBBER), P (PAPER), C (CLOTH/FABRIC), O (MIXED WASTE), and L (Large Debris items >1 m or >0.3 m depth)."
        ),
    },
    {
        "asset_id": "table_24",
        "title": "Table 24: Single-Use Plastic Waste Density at Each River Site Location",
        "page": 111,
        "bbox": [0.07, 0.42, 0.93, 0.86],
        "section": "Annex 2.1.C: Survey Results from River Sites",
        "content": (
            "[TABLE 24 | Page 111 | Annex 2.1.C] Table 24: Single-Use Plastic Waste Density at Each River Site Location (items/unit, where 1 river unit = 1 m2 x 0.3 m depth).\n"
            "| Province / Location | Single-Use Density (item/unit) | Other Plastic Density (item/unit) | Total Plastic Density (item/unit) | Single-Use Share (%) |\n"
            "| Can Tho | 24.9 | 9.7 | 34.5 | 72.2% |\n"
            "| Da Nang | 8.9 | 2.8 | 11.7 | 76.1% |\n"
            "| Hai Phong | 9.8 | 3.0 | 12.8 | 76.6% |\n"
            "| Ho Chi Minh | 21.9 | 11.5 | 33.4 | 65.6% |\n"
            "| Hue | 8.3 | 2.1 | 10.4 | 79.8% |\n"
            "| Khanh Hoa | 5.8 | 2.3 | 8.1 | 71.6% |\n"
            "| Lao Cai | 22.9 | 7.15 | 30.1 | 76.1% |\n"
            "| Phu Quoc | 7.0 | 2.6 | 9.6 | 72.9% |\n"
            "| Quang Nam | 6.4 | 3.0 | 9.4 | 68.1% |\n"
            "| Soc Trang | 4.0 | 0.3 | 4.3 | 93.0% |\n"
            "Key takeaways: Can Tho has the highest single-use plastic density (24.9 items/unit) and highest total river plastic density (34.5 items/unit), followed by Ho Chi Minh (33.4 total, 21.9 SUP) and Lao Cai (30.1 total, 22.9 SUP). Soc Trang has the lowest total density (4.3 items/unit; 4.0 SUP, 0.3 Other) but the highest SUP fraction (93.0%)."
        ),
    },
    {
        "asset_id": "table_25",
        "title": "Table 25: Detailed Proportional Waste Types by Hotspot Site (9 Drone Hotspots)",
        "page": 128,
        "bbox": [0.07, 0.14, 0.93, 0.91],
        "section": "Annex 2.2.C: Detailed Proportional Waste Types by Site",
        "content": (
            "[TABLE 25 | Pages 128-129 | Annex 2.2.C] Table 25: Detailed Proportional Waste Types by Site (9 Drone Survey Hotspots).\n"
            "| Waste Type | Thach Khoi 1 s1 | Thach Khoi 1 s2 | Chanh Duong 01 s1 | Chanh Duong 01 s2 | Chanh Duong 01 s3 | Chanh Duong 02 s1 | Chanh Duong 02 s2 | Suoi Cat 01_1 | Suoi Cat 01_2 |\n"
            "| Bags LDPE thick | 0% | 0% | 0% | 0% | 2% | 10% | 3% | 5% | 0% |\n"
            "| Bags LDPE | 4% | 2% | 11% | 15% | 38% | 13% | 49% | 16% | 7% |\n"
            "| Bags robust PET | 7% | 2% | 10% | 0% | 3% | 2% | 4% | 8% | 4% |\n"
            "| Wrappers under 10cm | 2% | 7% | 0% | 0% | 3% | 2% | 4% | 0% | 0% |\n"
            "| Wrappers over 10cm | 3% | 2% | 2% | 0% | 5% | 1% | 4% | 2% | 0% |\n"
            "| Bottles PET | 7% | 4% | 7% | 10% | 8% | 6% | 2% | 9% | 16% |\n"
            "| Polystyrene under 20cm (incl. food containers) | 36% | 44% | 43% | 18% | 23% | 23% | 19% | 14% | 26% |\n"
            "| Polystyrene over 20cm | 3% | 2% | 7% | 0% | 1% | 0% | 1% | 0% | 1% |\n"
            "| Fishing gear | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 2% | 0% |\n"
            "| Cup lids, caps and small plastics | 15% | 27% | 4% | 20% | 0% | 2% | 0% | 16% | 22% |\n"
            "| Other plastics over 20cm | 8% | 0% | 5% | 4% | 2% | 7% | 1% | 7% | 4% |\n"
            "| Rubber | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 2% | 0% |\n"
            "| Other non-plastics | 14% | 9% | 11% | 33% | 13% | 33% | 14% | 19% | 19% |"
        ),
    },
    {
        "asset_id": "table_26",
        "title": "Table 26: Flow Velocity Results from Net Sampling (Chanh Duong 2 Bridge)",
        "page": 130,
        "bbox": [0.07, 0.16, 0.93, 0.52],
        "section": "Annex 2.2.D: Flow Velocity Results from Net Sampling",
        "content": (
            "[TABLE 26 | Page 130 | Annex 2.2.D] Table 26: Flow Velocity Results from Net Sampling (m/s) at Chanh Duong 2 Bridge.\n"
            "| Time | Pos. 1 (GOPRO2) Upper net | Pos. 1 (GOPRO2) Lower net | Pos. 2 (GOPRO1) Upper net | Pos. 2 (GOPRO1) Lower net | Pos. 3 (GOPRO3) Upper net | Pos. 3 (GOPRO3) Lower net |\n"
            "| 8:30 AM | - | - | 0.26 m/s | 0.18 m/s | - | - |\n"
            "| 9:40 AM | 0.35 m/s | 0.24 m/s | - | - | - | - |\n"
            "| 10:20 AM | 0.41 m/s | 0.27 m/s | - | - | - | - |\n"
            "| 11:30 AM | - | - | 0.43 m/s | 0.30 m/s | - | - |\n"
            "| 1:20 PM | - | - | - | - | 0.58 m/s | 0.36 m/s |\n"
            "| 2:25 PM | - | - | - | - | 0.63 m/s | 0.41 m/s |\n"
            "Summary: Across all measurements, the upper net flow velocity (0.26 to 0.63 m/s) is consistently higher than the lower net flow velocity (0.18 to 0.41 m/s). Peak velocity was recorded at 2:25 PM at Pos. 3 (GOPRO3) with 0.63 m/s in the upper net and 0.41 m/s in the lower net."
        ),
    },
]


# ---------------------------------------------------------------------------
# Verified Visual Assets: 16 Image/Diagram + 38 Charts (Figure 1 .. Figure 54)
# ---------------------------------------------------------------------------
VERIFIED_FIGURES: list[dict[str, Any]] = [
    # --- IMAGE / DIAGRAM MODALITY (16 figures) ---
    {
        "asset_id": "fig_01",
        "modality": "image_diagram",
        "title": "Figure 1: Examples of Hotspots Investigated Through Drone Surveys (Hai Duong and Hai Phong)",
        "page": 20,
        "bbox": [0.11, 0.11, 0.89, 0.48],
        "section": "Executive Summary",
        "content": (
            "[FIGURE 1 | image_diagram | Page 20 | Executive Summary] Figure 1: Examples of hotspots investigated through drone surveys.\n"
            "Visual Layout: A 2x2 grid of low-altitude (6m height) UAV aerial photographs organized into two labeled columns:\n"
            "- Left column header: 'Hai Duong':\n"
            "  * Top-left photo label: 'Hai Duong, Thach Khoi 1, site 1' — shows a dense white accumulation of styrofoam boxes, plastic bags, and debris covering the riverbank next to a corrugated roof building with blue lettering 'SIEU THI NOI THAT'.\n"
            "  * Bottom-left photo label: 'Hai Duong, Thach Khoi 1, site 2' — shows heavy white plastic and styrofoam litter trapped along the muddy riverbank edge and vegetation.\n"
            "- Right column header: 'Hai Phong':\n"
            "  * Top-right photo label: 'Chanh Duong 01 (6m), Site 1' — shows floating plastic items entangled in green water hyacinth / aquatic vegetation in the river channel.\n"
            "  * Bottom-right photo label: 'Chanh Duong 02 (6m), site 2' — shows scattered plastic bags and styrofoam trapped in green riverside reeds and water hyacinth."
        ),
    },
    {
        "asset_id": "fig_04",
        "modality": "image_diagram",
        "title": "Figure 4: Overview Map of Survey Locations in Vietnam (River and Coastal Site Counts)",
        "page": 35,
        "bbox": [0.11, 0.12, 0.89, 0.90],
        "section": "2.1.3.1 Overview of Survey Sites",
        "content": (
            "[FIGURE 4 | image_diagram | Page 35 | Section 2.1.3.1] Figure 4: Overview of Survey Locations [R = River site, C = Coastal site].\n"
            "Visual Map Details: A map of Vietnam (with scale bar 0, 40, 80, 160 Kilometers, North arrow, 'East Sea', and 'Truong Sa' labeled) highlighting the 10 surveyed provinces/cities in blue with orange callout boxes showing exact River (R) and Coastal (C) site counts:\n"
            "1. Lao Cai (R: 4)\n"
            "2. Hai Phong (R: 2, C: 2)\n"
            "3. Thua Thien Hue (R: 2, C: 1)\n"
            "4. Da Nang (R: 4, C: 2) [Note: map callout prints 'Da Nang (R: 4, C: 2)' whereas Table 1 & Table 5 list 2 river and 2 coastal sites in Da Nang]\n"
            "5. Quang Nam (R: 2, C: 1)\n"
            "6. Khanh Hoa (R: 3, C: 3)\n"
            "7. Phu Quoc (R: 2, C: 2)\n"
            "8. Ho Chi Minh (R: 2, C: 1)\n"
            "9. Can Tho (R: 3)\n"
            "10. Soc Trang (R: 2, C: 2)\n"
            "Only two locations on the map have zero coastal sites (R only): Lao Cai (R: 4) and Can Tho (R: 3)."
        ),
    },
    {
        "asset_id": "fig_09",
        "modality": "image_diagram",
        "title": "Figure 9: Field Photos of the Top 10 Plastic Waste Items at River and Coastal Sites in Vietnam",
        "page": 41,
        "bbox": [0.08, 0.51, 0.92, 0.90],
        "section": "2.1.3.2 Combined Results from Both River and Coastal Surveys",
        "content": (
            "[FIGURE 9 | image_diagram | Page 41 | Section 2.1.3.2] Figure 9: Photos of the Top 10 Plastic Waste Items at River and Coastal Sites in Vietnam.\n"
            "Visual Layout: A 3-row photo collage displaying representative field photographs of each of the Top 10 plastic items:\n"
            "- Row 1 (4 photos, left to right): 'Soft plastic fragments', 'Fishing gear 1' (tangled green monofilament nets and ropes), 'Fishing gear 2' (broken white EPS styrofoam floats), 'Plastic bags 0-5kg' (thin blue/pink/yellow single-use carrier bags).\n"
            "- Row 2 (4 photos, left to right): 'Styrofoam food containers' (crushed white clamshell meal boxes), 'Straws' (assorted colored plastic drinking straws), 'Other food wrappers' (instant noodle/snack pouches), 'Other plastic' (blue foam flip-flop sandal).\n"
            "- Row 3 (2 photos, centered): 'Hard plastic fragments' (broken rigid red/pink plastic pieces), 'Crip/sweet packages' (spelled 'Crip/sweet packages' in caption; silver/red confectionery wrappers)."
        ),
    },
    {
        "asset_id": "fig_24",
        "modality": "image_diagram",
        "title": "Figure 24: Map of Remote Sensing Survey Locations and Survey Sites (Sapa, Hai Duong, Hai Phong)",
        "page": 60,
        "bbox": [0.09, 0.11, 0.91, 0.88],
        "section": "2.2.2 Selection of Study Locations",
        "content": (
            "[FIGURE 24 | image_diagram | Page 60 | Section 2.2.2] Figure 24: Map of Survey Locations and Survey Sites.\n"
            "Visual Map Details: Northern Vietnam regional map (scale 1 cm = 40 km, 0 to 200 Kilometers, WAREC / DF / BOKU logos) with Legend (Surveying locations = white circles, Province = light blue, River = blue line, Bridge = magenta line, Road = brown line) and three zoomed-in inset maps numbered 1, 2, and 3:\n"
            "- Inset 1 (Sapa, Lao Cai Province, top-left): shows 3 sites along the stream from west to east: 'Suoi Cat 3', 'Suoi Cat 2', and 'Suoi Cat 1'.\n"
            "- Inset 2 (Hai Duong Province, top-right): shows 3 sites from north to south: 'Han bridge', 'Thach Khoi 1', and 'Thach Khoi 2'.\n"
            "- Inset 3 (Hai Phong City, bottom-right): shows 3 sites: 'Dang bridge' in the north, and 'Chanh Duong 2' and 'Chanh Duong 1' along the southern tributary."
        ),
    },
    {
        "asset_id": "fig_25",
        "modality": "image_diagram",
        "title": "Figure 25: Data Collection Devices Utilized in the Field Work (Bridge Camera, UAV Drone, Net Trawl)",
        "page": 62,
        "bbox": [0.08, 0.56, 0.92, 0.85],
        "section": "2.2.3.1 Data Collection and Field Work",
        "content": (
            "[FIGURE 25 | image_diagram | Page 62 | Section 2.2.3.1] Figure 25: Data Collection Devices Utilized in the Field Work.\n"
            "Visual Layout: Three side-by-side field photographs illustrating the three complementary monitoring technologies:\n"
            "- Left photo: Stationary GoPro bridge camera mounted on an extension pole clamped to a rusty bridge railing, being configured via smartphone app by a field engineer.\n"
            "- Center photo: White quadcopter UAV (drone, DJI Phantom series) flying over a vegetated riverbank wall to capture aerial orthomosaics.\n"
            "- Right photo: Metal net-sampling frame with blue trawl nets deployed vertically into the river water column beneath a concrete bridge."
        ),
    },
    {
        "asset_id": "fig_26",
        "modality": "image_diagram",
        "title": "Figure 26: Example of a Typical Survey Protocol at a River Site (Cau Rao Bridge, Hai Phong)",
        "page": 63,
        "bbox": [0.08, 0.41, 0.92, 0.86],
        "section": "2.2.3.1 Data Collection and Field Work",
        "content": (
            "[FIGURE 26 | image_diagram | Page 63 | Section 2.2.3.1] Figure 26: Example of a Typical Survey Protocol (Cau Rao Bridge in Hai Phong on the Lach Tray River, scale 1:3,800, 0–200 Meters).\n"
            "Visual Diagram Details: Schematic GIS map illustrating the spatial layout of a river monitoring site around 'Cau Rao bridge' (magenta line crossing 'Lach Tray river' between 'Ngo Quyen', 'Le Chan', 'Hai An', and 'Duong Kinh' districts):\n"
            "- 'Plastic flow monitoring section': along the bridge cross-section (Surveying location 1).\n"
            "- 'High altitude flight area' (light green polygon, captured at 60–100 m altitude): extends 250 m upstream and 250 m downstream from the bridge (total 500 m length along river), with upper and lower edges fixed at 100 m from the riverbanks on both sides.\n"
            "- 'Low altitude flight area (10 x 10m survey box)' (dark green squares, captured at 3–6 m altitude): multiple 10 m x 10 m boxes placed over accumulated plastic hotspots along the riverbanks.\n"
            "Note beneath figure: 'The map shows Cau Rao Bridge in Hai Phong as an example of a typical survey protocol. No survey was undertaken at this site.'"
        ),
    },
    {
        "asset_id": "fig_27",
        "modality": "image_diagram",
        "title": "Figure 27: Pictures of Pollution Hotspots in Hai Duong and Hai Phong",
        "page": 66,
        "bbox": [0.11, 0.08, 0.89, 0.49],
        "section": "2.2.4.1 Results of the Drone Surveys",
        "content": (
            "[FIGURE 27 | image_diagram | Page 66 | Section 2.2.4.1] Figure 27: Pictures of Pollution Hotspots in Hai Duong and Hai Phong.\n"
            "Visual Layout: 2x2 grid of low-altitude (6m) UAV hotspot photos (identical scene set to Figure 1): Left column 'Hai Duong' ('Hai Duong, Thach Khoi 1, site 1' top; 'Hai Duong, Thach Khoi 1, site 2' bottom) showing massive white styrofoam/plastic bank accumulations (5,507 items across 45 m2); Right column 'Hai Phong' ('Chanh Duong 01 (6m), Site 1' top; 'Chanh Duong 02 (6m), site 2' bottom) showing plastic debris trapped in floating water hyacinth."
        ),
    },
    {
        "asset_id": "fig_45",
        "modality": "image_diagram",
        "title": "Figure 45: Camera Installation at the Bridge (GoPro RGB 15-20 MP / 4K Time-Lapse Setup)",
        "page": 116,
        "bbox": [0.21, 0.48, 0.78, 0.87],
        "section": "Annex 2.2.A: Key Methodologies",
        "content": (
            "[FIGURE 45 | image_diagram | Page 116 | Annex 2.2.A] Figure 45: Camera installation at the bridge.\n"
            "Visual & Technical Details: Shows a field researcher operating a smartphone connected to a bridge-mounted GoPro RGB camera on a horizontal boom arm extending out from the bridge parapet over the river. "
            "Three GoPro cameras were installed on bridges per site (recording 8 hours each per camera = 24-hour footage per survey site) using RGB cameras with 15–20 MP resolution and 4K video recording."
        ),
    },
    {
        "asset_id": "fig_46",
        "modality": "image_diagram",
        "title": "Figure 46: UAV Operation at a Survey Location (Two-Step 60-100m and 6m Flight Protocol)",
        "page": 117,
        "bbox": [0.21, 0.27, 0.78, 0.74],
        "section": "Annex 2.2.A: Key Methodologies",
        "content": (
            "[FIGURE 46 | image_diagram | Page 117 | Annex 2.2.A] Figure 46: UAV operation at a survey location.\n"
            "Visual & Technical Details: Photograph of a white quadcopter drone hovering over a river channel bordered by concrete retaining walls and dense greenery. "
            "Two sets of imagery were captured: (1) high-spatial-resolution overview imagery at a high flight altitude of 60–100 m (~250 m upstream/downstream, 100 m bank buffer), and (2) very-high-spatial-resolution imagery at a low flight altitude of 6 m (10 m x 10 m hotspot boxes) achieving a ground sampling distance (GSD) of ~0.2 cm."
        ),
    },
    {
        "asset_id": "fig_47",
        "modality": "image_diagram",
        "title": "Figure 47: Final Device Configuration of Multi-Depth Net Trawls (3 Vertical Layers)",
        "page": 118,
        "bbox": [0.24, 0.22, 0.75, 0.73],
        "section": "Annex 2.2.A: Key Methodologies",
        "content": (
            "[FIGURE 47 | image_diagram | Page 118 | Annex 2.2.A] Figure 47: Final device configuration of net trawls.\n"
            "Visual Diagram & Specifications: Annotated photograph of the vertical 3-tier net trawl carrier suspended over a river, with callout specifications for each depth layer:\n"
            "1. 'Water surface sampling' (top tier):\n"
            "   - openings: 600x600 mm\n"
            "   - nets: 500 um, 250 um\n"
            "   - buoyant bodies (black cylindrical floats on sides)\n"
            "   - fins, inclination rack, mechanical flow meter\n"
            "2. 'Middle of water column' (middle tier):\n"
            "   - openings: 600x600 mm\n"
            "   - nets: 500 um, 250 um, optional 41 um net\n"
            "   - fins, inclination rack, mechanical flow meter\n"
            "3. 'Near-bed sampling' (bottom tier):\n"
            "   - basket sampler, heavy loads (red torpedo weights on base)\n"
            "   - opening: 300x600 mm\n"
            "   - net: 500 um\n"
            "   - fins, mechanical flow meter\n"
            "Caption notes: 1–7 vertical profiles are distributed over the wetted cross-section, yielding a maximum of 35 sampling points per deployment (~45 to 120 minutes exposure)."
        ),
    },
    {
        "asset_id": "fig_48",
        "modality": "image_diagram",
        "title": "Figure 48: APLASTIC-Q Two-Stage Convolutional Neural Network (PLD-CNN and PLQ-CNN) Architecture",
        "page": 119,
        "bbox": [0.08, 0.42, 0.92, 0.72],
        "section": "Annex 2.2.A: Data Analysis",
        "content": (
            "[FIGURE 48 | image_diagram | Page 119 | Annex 2.2.A] Figure 48: APLASTIC-Q (Wolf et al. 2020) analysis of imagery based on convolutional neural networks.\n"
            "Visual Flowchart Stages (left to right, a to d):\n"
            "- (a) Input image: Low-altitude (6m, GSD 0.2 cm) drone image partitioned into two tile sizes: 128x128x3 pixels (shown as 100x100x3 in diagram graphic) for PLD-CNN and 64x64x3 pixels (50x50x3 in diagram graphic) for PLQ-CNN.\n"
            "- (b) Classification of input image parts in two different sizes with two ML-components:\n"
            "  * Stage 1 'PLD-CNN' (Plastic Litter Detection CNN): classifies tiles into 6 classes: Water (45), Vegetation (1), Sand (0), Litter - high (21), Litter - low (31), Other (0).\n"
            "  * Stage 2 'PLQ-CNN' (Plastic Litter Quantification CNN): restricted to areas classified as Litter-high or Litter-low; classifies into specific pollutant types (Cans, Carton, Plastic bag - large [14], Plastic bag - small [26], Plastic bottles [28], Plastic bowls, Plastic canister, Plastic cups, Polystyrene packaging [31], Shoes, String and cord, Styrofoam [45], Textiles, etc.).\n"
            "- (c) Altitude corrected counts of class areas (applying true altitude and litter-density / pollutant-size parameters).\n"
            "- (d) Assessment of class-object counts: outputs 'Est. No. of litter items: 120' and 'Est. No. for each pollutant'.\n"
            "Volume calculation rule in text below Figure 48: Tiles classified as 'Litter-low' are considered 50% polluted with average thickness 7 cm; tiles classified as 'Litter-high' are considered 100% polluted with average thickness 30 cm (e.g. a 128x128 tile at GSD 0.2 cm has real-world area 0.065 m2 -> Litter-high waste volume = 0.019 m3)."
        ),
    },
    {
        "asset_id": "fig_49",
        "modality": "image_diagram",
        "title": "Figure 49: Example Output of APLASTIC-Q on Scene parola_phantomq1_transparent_mosaic_group1",
        "page": 120,
        "bbox": [0.08, 0.45, 0.92, 0.86],
        "section": "Annex 2.2.A: Plastic Detection, Classification and Quantification",
        "content": (
            "[FIGURE 49 | image_diagram | Page 120 | Annex 2.2.A] Figure 49: Example output of APLASTIC-Q ('Scene: parola_phantomq1_transparent_mosaic_group1').\n"
            "Visual Dashboard Output Panels:\n"
            "1. Top-left: Input orthomosaic image and 'Classification matrix PLD CNN' heatmap.\n"
            "2. Top-right table 'Estimated areas and pollution items - PLD CNN':\n"
            "   - Litter - high: 377 tiles\n"
            "   - Litter - low: 746 tiles\n"
            "   - Other: 156 | Sand: 676 | Vegetation: 1273 | Water: 326\n"
            "   - Est. no. of items: 3,377\n"
            "   - m2 est. (estimated polluted area): 30 m2\n"
            "   - m3 est. (estimated waste volume): 6 m3\n"
            "3. Bottom-left pie chart 'Share of waste types': P - cup lids, caps and small plastics (45%), P - polystyrene under 20cm (15%), NP - other (13%), P - wrappers over 10cm (8%), P - bags robust PET (7%), P - wrappers under 10cm (6%), P - bottles PET (4%), P - bags LDPE (3%).\n"
            "4. Bottom-right table 'Estimated areas and pollution items - PLQ CNN' (Classifications vs Est. types): P - cup lids, caps and small plastics (747 classifications -> 1,494 est. types), P - polystyrene under 20cm (555 -> 555), NP - other (479 -> 479), P - bags robust PET (421 -> 210), P - wrappers over 10cm (295 -> 295), P - wrappers under 10cm (135 -> 270), P - bottles PET (154 -> 154), P - bags LDPE (100 -> 100), P - polystyrene over 20cm (105 -> 31), P - other plastics over 20cm (101 -> 70), P - bags LDPE thick (6 -> 3), P - fishing gear (8 -> 4), NP - rubber (20 -> 10)."
        ),
    },
    {
        "asset_id": "fig_51",
        "modality": "image_diagram",
        "title": "Figure 51: Visualization of Construction Plan of Equipment Carrier (Left) and Field Test (Right)",
        "page": 125,
        "bbox": [0.08, 0.24, 0.92, 0.54],
        "section": "Annex 2.2.B: Development of a Net Sampling Device",
        "content": (
            "[FIGURE 51 | image_diagram | Page 125 | Annex 2.2.B] Figure 51: Visualization of the construction plan of the equipment carrier (left); field test of the newly developed equipment carrier (right).\n"
            "Visual & Engineering Specifications:\n"
            "- Left image: 3D CAD rendering of the steel equipment carrier frame showing a 600x600 mm vertical rectangular front net frame connected by two lower cross-beams to a rear stabilizing fin, with 3 circular weight plates on each side.\n"
            "- Right image: Field test photo showing the carrier being crane-lifted out of a river with green mesh net and circular steel weights attached.\n"
            "- Accompanying specifications on Page 125: Frame consists of 48 mm steel pipes; macro-plastic net frame dimensions are 600x600 mm; non-welded bolted connections allow rapid disassembly; 12 threaded bars welded to frame each hold two ~10 kg weights = 240 kg additional ballast weight. Four mesh sizes were tested: 250 um (34% porosity, 2.5 m length), 500 um (38% porosity, 2.5 m length), 2.43 mm (44% porosity), and 8 mm (undefined porosity); the 2.43 mm mesh is recommended for macro-plastic sampling."
        ),
    },
    {
        "asset_id": "fig_52",
        "modality": "image_diagram",
        "title": "Figure 52: Assemblage of the Macro Plastic Measurement Device (Old vs Newly Developed Configuration)",
        "page": 126,
        "bbox": [0.25, 0.42, 0.75, 0.90],
        "section": "Annex 2.2.B: Frame Size and Device Assemblage",
        "content": (
            "[FIGURE 52 | image_diagram | Page 126 | Annex 2.2.B] Figure 52: Assemblage of the macro plastic measurement device.\n"
            "Visual Layout (2x2 photo grid):\n"
            "- Top-left: Old assemblage suspended by crane (white fine-mesh nets with red bottom torpedo weights).\n"
            "- Top-right: Newly developed configuration suspended by crane (green coarse-mesh nets, 1.6 m middle stabilizing fin, and bottom carrier frame with 240 kg circular weights).\n"
            "- Bottom-left: Close-up of nets with inclination rack keeping the net opening upright.\n"
            "- Bottom-right: Uppermost surface net layer floating on the river surface supported by black buoyant bodies."
        ),
    },
    {
        "asset_id": "fig_53",
        "modality": "image_diagram",
        "title": "Figure 53: Sampling Container Used for Emptying the Nets",
        "page": 127,
        "bbox": [0.11, 0.08, 0.88, 0.43],
        "section": "Annex 2.2.B: Development of a Net Sampling Device",
        "content": (
            "[FIGURE 53 | image_diagram | Page 127 | Annex 2.2.B] Figure 53: Sampling container used for emptying the nets.\n"
            "Visual Details: Two side-by-side close-up photos: Left shows the cylindrical white PVC cod-end sampling container (Liedermann et al. 2018 design) clamped with quick-release metal hose clamps to the tail of the net; Right shows the detached cylinder emptying collected dark river debris and plastic fragments into a white plastic sorting basin."
        ),
    },
    {
        "asset_id": "fig_54",
        "modality": "image_diagram",
        "title": "Figure 54: Mechanical Flow Meter (HYDRO-BIOS) Attached at the Inlet of the Net",
        "page": 127,
        "bbox": [0.09, 0.46, 0.91, 0.72],
        "section": "Annex 2.2.B: Development of a Net Sampling Device",
        "content": (
            "[FIGURE 54 | image_diagram | Page 127 | Annex 2.2.B] Figure 54: Mechanical flow meter attached at the inlet of the net to measure the discharge.\n"
            "Visual Details: Two side-by-side photos: Left shows a close-up of the white torpedo-shaped mechanical impeller flow meter labeled 'HYDRO-BIOS' with a 5-digit mechanical counter window suspended on a vertical wire; Right shows the HYDRO-BIOS flow meter mounted centrally inside the 600x600 mm stainless-steel net inlet frame to measure water flow velocity and discharge through the net."
        ),
    },

    # --- CHART MODALITY (38 figures) ---
    {
        "asset_id": "fig_02",
        "modality": "chart",
        "title": "Figure 2: Percentages of Top 10 Polluting Plastic Items on Riverbanks by Density and Weight",
        "page": 20,
        "bbox": [0.12, 0.51, 0.88, 0.88],
        "section": "Executive Summary",
        "content": (
            "[FIGURE 2 | chart | Page 20 | Executive Summary] Figure 2: Percentages of the top 10 polluting plastic items on riverbanks by density (items per unit, left axis 0–4.5 item.unit^-1, blue bars) and weight (weight per unit, right axis 0–25 gram.unit^-1, green dots).\n"
            "Exact Data Series (10 items ordered left to right by density):\n"
            "1. Plastic bags size 1: Density = 21.9% (~3.95 item.unit^-1) | Weight = 14% (~17.8 gram.unit^-1)\n"
            "2. Styrofoam food containers: Density = 11.4% (~2.05 item.unit^-1) | Weight = 4% (~5.5 gram.unit^-1)\n"
            "3. Soft plastic fragments: Density = 10.8% (~1.95 item.unit^-1) | Weight = 3% (~4.2 gram.unit^-1)\n"
            "4. Food wrappers: Density = 8.8% (~1.6 item.unit^-1) | Weight = 1% (~1.8 gram.unit^-1)\n"
            "5. Crisp/Sweet packages: Density = 5.8% (~1.05 item.unit^-1) | Weight = 2% (~2.3 gram.unit^-1)\n"
            "6. Plastic strings, cords and ropes: Density = 5.7% (~1.02 item.unit^-1) | Weight = 4% (~5.2 gram.unit^-1)\n"
            "7. Other plastic: Density = 4.7% (~0.85 item.unit^-1) | Weight = 6% (~7.3 gram.unit^-1)\n"
            "8. Hard plastic fragments: Density = 4.6% (~0.82 item.unit^-1) | Weight = 15% (~18.7 gram.unit^-1, highest weight share on riverbanks!)\n"
            "9. Other wrappers: Density = 4.1% (~0.75 item.unit^-1) | Weight = 2% (~2.0 gram.unit^-1)\n"
            "10. Fishing gear 2: Density = 3.5% (~0.62 item.unit^-1) | Weight = 3% (~3.5 gram.unit^-1)\n"
            "Total Top 10 on riverbanks = 81.3% of total plastic density and 54% of total plastic weight."
        ),
    },
    {
        "asset_id": "fig_03",
        "modality": "chart",
        "title": "Figure 3: Percentages of Top 10 Polluting Plastic Items at Coastal Sites by Density and Weight",
        "page": 21,
        "bbox": [0.13, 0.11, 0.87, 0.44],
        "section": "Executive Summary",
        "content": (
            "[FIGURE 3 | chart | Page 21 | Executive Summary] Figure 3: Percentages of the top 10 polluting plastic items at coastal sites by density (items per meter of coastline, left axis 0–16 items.m^-1, blue bars = number) and weight (weight per meter of coastline, right axis 0–80 gram.m^-1, grey dots = weight).\n"
            "Exact Data Series (10 items ordered left to right by density):\n"
            "1. Fishing gear 1: Number/Density = 18.5% (~13.9 items.m^-1) | Weight = 19.1% (~69 gram.m^-1)\n"
            "2. Soft plastic fragments: Number/Density = 18.1% (~13.6 items.m^-1) | Weight = 16.2% (~58 gram.m^-1)\n"
            "3. Fishing gear 2: Number/Density = 14.0% (~10.5 items.m^-1) | Weight = 12.8% (~46 gram.m^-1)\n"
            "4. Plastic bags size 1: Number/Density = 7.1% (~5.3 items.m^-1) | Weight = 8.3% (~30 gram.m^-1)\n"
            "5. Styrofoam food containers: Number/Density = 6.8% (~5.1 items.m^-1) | Weight = 0.8% (~3 gram.m^-1)\n"
            "6. Hard plastic fragments: Number/Density = 6.4% (~4.8 items.m^-1) | Weight = 3.8% (~14 gram.m^-1)\n"
            "7. Straws: Number/Density = 4.9% (~3.7 items.m^-1) | Weight = 0.7% (~2.5 gram.m^-1)\n"
            "8. Other plastics: Number/Density = 2.8% (~2.1 items.m^-1) | Weight = 11.7% (~42 gram.m^-1)\n"
            "9. Crisp/Sweet packages: Number/Density = 2.8% (~2.1 items.m^-1) | Weight = 0.9% (~3.2 gram.m^-1)\n"
            "10. Other food wrappers: Number/Density = 2.6% (~1.95 items.m^-1) | Weight = 1.0% (~3.6 gram.m^-1)\n"
            "Total Top 10 at coastal sites = 84% of total plastic density and 75.3% (75.5% in text) of total plastic weight. Combined fisheries-related waste (Fishing gear 1 + Fishing gear 2) = 18.5% + 14.0% = 32.5% by density and 19.1% + 12.8% = 31.9% by weight."
        ),
    },
    {
        "asset_id": "fig_05",
        "modality": "chart",
        "title": "Figure 5: Total Number of Waste Items (Percentage) on Surveyed Sites in Vietnam",
        "page": 39,
        "bbox": [0.14, 0.23, 0.86, 0.56],
        "section": "2.1.3.2 Combined Results from Both River and Coastal Surveys",
        "content": (
            "[FIGURE 5 | chart | Page 39 | Section 2.1.3.2] Figure 5: Total Number of Waste Items (percentage) on Surveyed Sites in Vietnam (38 river + coastal sites combined, total 109,259 waste items).\n"
            "Chart Type: Pie-of-pie chart.\n"
            "- Main Pie Slices: Plastic = 93.6% | Glass = 1.4% | Metal = 0.7% | Rubber = 0.6% | Other = 3.6%.\n"
            "- Secondary Breakout Pie (breaking down 'Other, 3.6%'): Mix waste = 1.5% | Cloth/fabric = 1.5% | Paper/timber = 0.6%."
        ),
    },
    {
        "asset_id": "fig_06",
        "modality": "chart",
        "title": "Figure 6: Total Weight of Waste (Percentage) on Surveyed Sites in Vietnam 2020",
        "page": 39,
        "bbox": [0.14, 0.57, 0.86, 0.90],
        "section": "2.1.3.2 Combined Results from Both River and Coastal Surveys",
        "content": (
            "[FIGURE 6 | chart | Page 39 | Section 2.1.3.2] Figure 6: Total Weight of Waste (percentage) on Surveyed Sites in Vietnam 2020 (total 757.8 kg of waste).\n"
            "Chart Type: Pie-of-pie chart.\n"
            "- Main Pie Slices: Plastic = 70.7% | Glass = 8.9% | Metal = 3.3% | Rubber = 3.0% | Other = 14.1%.\n"
            "- Secondary Breakout Pie (breaking down 'Other, 14.1%'): Mix waste = 6.6% | Cloth/fabric = 5.1% | Paper/timber = 2.4%."
        ),
    },
    {
        "asset_id": "fig_07",
        "modality": "chart",
        "title": "Figure 7: Total Number and Weight of Plastic Waste by Source on Surveyed Sites in Vietnam 2020",
        "page": 40,
        "bbox": [0.08, 0.10, 0.92, 0.44],
        "section": "2.1.3.2 Combined Results from Both River and Coastal Surveys",
        "content": (
            "[FIGURE 7 | chart | Page 40 | Section 2.1.3.2] Figure 7: Total Number and Weight of Plastic Waste by Source on Surveyed Sites in Vietnam 2020 (two side-by-side pie charts).\n"
            "- Left Pie Chart ('Number'):\n"
            "  1. Take-away related: 43.6%\n"
            "  2. Fisheries-related: 32.6%\n"
            "  3. Household: 21.6%\n"
            "  4. Agriculture-related: 1.1%\n"
            "  5. Sanitary and Medical-related: 1.1%\n"
            "- Right Pie Chart ('Weight'):\n"
            "  1. Take-away related: 35.1%\n"
            "  2. Fisheries-related: 30.6%\n"
            "  3. Household: 22.8%\n"
            "  4. Agriculture-related: 8.2%\n"
            "  5. Sanitary and Medical-related: 3.3%"
        ),
    },
    {
        "asset_id": "fig_08",
        "modality": "chart",
        "title": "Figure 8: Top 10 Plastic Waste Items at River and Coastal Sites in Vietnam (Combined Number & Weight)",
        "page": 41,
        "bbox": [0.11, 0.08, 0.89, 0.49],
        "section": "2.1.3.2 Combined Results from Both River and Coastal Surveys",
        "content": (
            "[FIGURE 8 | chart | Page 41 | Section 2.1.3.2] Figure 8: Top 10 Plastic Waste Items at River and Coastal Sites in Vietnam (Left axis: Total number in items 0–4,500, blue bars; Right axis: Total weight in grams 0–25,000, green dots).\n"
            "Exact Data Series (10 items left to right):\n"
            "1. Soft plastic fragments: Number = 17.4% (~3,980 items) | Weight = 14.5% (~16,800 g)\n"
            "2. Fishing gear 1: Number = 16.9% (~3,870 items) | Weight = 17.3% (~20,000 g, highest total weight!)\n"
            "3. Fishing gear 2: Number = 13.0% (~2,970 items) | Weight = 11.5% (~13,300 g)\n"
            "4. Plastic bags size 1: Number = 8.5% (~1,950 items) | Weight = 9.1% (~10,500 g)\n"
            "5. Styrofoam food containers: Number = 7.2% (~1,650 items) | Weight = 1.3% (~1,500 g)\n"
            "6. Hard plastic fragments: Number = 6.2% (~1,420 items) | Weight = 5.3% (~6,100 g)\n"
            "7. Straws: Number = 4.7% (~1,080 items) | Weight = 0.6% (~700 g)\n"
            "8. Other food wrappers: Number = 3.1% (~710 items) | Weight = 1.1% (~1,270 g)\n"
            "9. Crisp/Sweet packages: Number = 3.1% (~710 items) | Weight = 1.1% (~1,270 g)\n"
            "10. Other plastic: Number = 3.0% (~690 items) | Weight = 10.9% (~12,600 g)"
        ),
    },
    {
        "asset_id": "fig_10",
        "modality": "chart",
        "title": "Figure 10: Percentage of Single-Use Plastic Waste at River and Coastal Sites",
        "page": 42,
        "bbox": [0.10, 0.08, 0.90, 0.36],
        "section": "2.1.3.2 Combined Results from Both River and Coastal Surveys",
        "content": (
            "[FIGURE 10 | chart | Page 42 | Section 2.1.3.2] Figure 10: Percentage of Single-use Plastic Waste at River and Coastal Sites (two side-by-side pie charts).\n"
            "- Left Pie Chart ('River sites'): Single use waste items = 72% | Other plastic waste items = 28%.\n"
            "- Right Pie Chart ('Coastal sites'): Single use waste items = 52% | Other plastic waste items = 48%."
        ),
    },
    {
        "asset_id": "fig_11",
        "modality": "chart",
        "title": "Figure 11: Total Number of Waste Items (Percentage) at Surveyed River Sites",
        "page": 42,
        "bbox": [0.14, 0.61, 0.86, 0.90],
        "section": "2.1.3.3 Results from the Surveys Conducted at River Sites",
        "content": (
            "[FIGURE 11 | chart | Page 42 | Section 2.1.3.3] Figure 11: Total Number of Waste Items (percentage) at Surveyed River Sites (96 transects across 24 river sites in 10 locations: 7,610 pieces and 219 kg of debris).\n"
            "Pie Chart Values: Plastic = 79.7% | Mixed waste = 6.6% | Glass = 6.2% | Cloth/fabric = 3.0% | Paper/timber = 2.5% | Metal = 1.1% | Rubber = 0.9%."
        ),
    },
    {
        "asset_id": "fig_12",
        "modality": "chart",
        "title": "Figure 12: Total Weight of Waste (Percentage) at Surveyed River Sites",
        "page": 44,
        "bbox": [0.14, 0.08, 0.86, 0.38],
        "section": "2.1.3.3 Results from the Surveys Conducted at River Sites",
        "content": (
            "[FIGURE 12 | chart | Page 44 | Section 2.1.3.3] Figure 12: Total Weight of Waste (percentage) at Surveyed River Sites.\n"
            "Pie Chart Values: Plastic = 57.20% | Glass = 9.60% | Mixed waste = 9.40% | Paper/timber = 7.80% | Cloth/fabric = 7.70% | Metal = 5.90% | Rubber = 2.50%."
        ),
    },
    {
        "asset_id": "fig_13",
        "modality": "chart",
        "title": "Figure 13: Total Density and Weight of Plastic Waste by Source on Surveyed River Sites in Vietnam",
        "page": 44,
        "bbox": [0.12, 0.51, 0.88, 0.89],
        "section": "2.1.3.3 Results from the Surveys Conducted at River Sites",
        "content": (
            "[FIGURE 13 | chart | Page 44 | Section 2.1.3.3] Figure 13: Total Density and Weight of Plastic Waste by Source on Surveyed River Sites in Vietnam (Left axis: items.unit^-1 0–10, blue bars = Density; Right axis: gram 0–40, green dots = Weight).\n"
            "Exact Values by Source (5 sources):\n"
            "1. Fisheries-related: Density = 10.6% (~1.8 items.unit^-1) | Weight = 12.4% (~16.2 g)\n"
            "2. Agriculture-related: Density = 3.1% (~0.5 items.unit^-1) | Weight = 14.4% (~18.8 g)\n"
            "3. Take-away related: Density = 50.0% (~8.7 items.unit^-1) | Weight = 27.3% (~35.5 g)\n"
            "4. Household: Density = 33.3% (~5.8 items.unit^-1) | Weight = 29.0% (~37.7 g, highest weight share by source on rivers!)\n"
            "5. Medical-related: Density = 2.9% (~0.5 items.unit^-1) | Weight = 16.9% (~22.0 g)"
        ),
    },
    {
        "asset_id": "fig_14",
        "modality": "chart",
        "title": "Figure 14: Top 10 Plastic Waste Items at River Sites in Vietnam (Density & Weight)",
        "page": 45,
        "bbox": [0.10, 0.19, 0.90, 0.55],
        "section": "2.1.3.3 Results from the Surveys Conducted at River Sites",
        "content": (
            "[FIGURE 14 | chart | Page 45 | Section 2.1.3.3] Figure 14: Top 10 Plastic Waste Items at River Sites in Vietnam (same data series as Figure 2: Plastic bags size 1 21.9% density / 14% weight; Styrofoam food containers 11.4% / 4%; Soft plastic fragments 10.8% / 3%; Food wrappers 8.8% / 1%; Crisp/Sweet packages 5.8% / 2%; Plastic strings, cords and ropes 5.7% / 4%; Other plastic 4.7% / 6%; Hard plastic fragments 4.6% / 15% weight; Other wrappers 4.1% / 2%; Fishing gear 2 3.5% / 3%).\n"
            "Page 45 text also notes average river plastic density by river basin: Dong Nai-Sai Gon River = 33 items/unit, Red River = 24 items/unit, Mekong River = 22 items/unit, Central rivers = 9 items/unit, Phu Quoc rivers = 9 items/unit."
        ),
    },
    {
        "asset_id": "fig_15",
        "modality": "chart",
        "title": "Figure 15: Top 10 Plastic Waste Items at River Sites in Rural and Urban Areas by Density",
        "page": 46,
        "bbox": [0.09, 0.25, 0.91, 0.55],
        "section": "2.1.3.3 Results from the Surveys Conducted at River Sites",
        "content": (
            "[FIGURE 15 | chart | Page 46 | Section 2.1.3.3] Figure 15: Top 10 Plastic Waste Items at River Sites in Rural and Urban Areas by Density (horizontal bar charts, axis 0–6 Item.unit^-1).\n"
            "- Left Panel ('Rural river', top 10 = 83.8% of plastic waste):\n"
            "  1. Plastic bags size 1: 20.6% (~2.5 Item.unit^-1)\n"
            "  2. Styrofoam food container: 13.5% (~1.6 Item.unit^-1)\n"
            "  3. Plastic strings, cords and ropes: 9.5%\n"
            "  4. Food wrappers: 9.5%\n"
            "  5. Soft plastic fragment: 9.3%\n"
            "  6. Other plastic: 5.8%\n"
            "  7. Fishing gear 2: 5.1%\n"
            "  8. Crisp/Sweet packages: 4.0%\n"
            "  9. Fertilizer Bags or containers: 3.5% (unique to Rural river top 10!)\n"
            "  10. Hard plastic fragment: 2.9%\n"
            "- Right Panel ('Urban river', top 10 = 81.0% of plastic waste):\n"
            "  1. Plastic bags size 1: 22.4% (~4.8 Item.unit^-1)\n"
            "  2. Soft plastic fragment: 11.3% (~2.4 Item.unit^-1)\n"
            "  3. Styrofoam food container: 10.6%\n"
            "  4. Food wrappers: 8.5%\n"
            "  5. Crisp/Sweet packages: 6.5%\n"
            "  6. Hard plastic fragment: 5.2%\n"
            "  7. Other wrappers: 4.7% (unique to Urban river top 10!)\n"
            "  8. Plastic strings, cords and ropes: 4.5%\n"
            "  9. Other plastic: 4.3%\n"
            "  10. Fishing gear 2: 3.0%"
        ),
    },
    {
        "asset_id": "fig_16",
        "modality": "chart",
        "title": "Figure 16: Top 10 Plastic Waste Items at Tourist and Non-Tourist River Sites by Density",
        "page": 47,
        "bbox": [0.11, 0.08, 0.89, 0.35],
        "section": "2.1.3.3 Results from the Surveys Conducted at River Sites",
        "content": (
            "[FIGURE 16 | chart | Page 47 | Section 2.1.3.3] Figure 16: Top 10 Plastic Waste Items at Tourist and Non-tourist River Sites by Density.\n"
            "- Left Panel ('Tourist', axis 0–4 Item.unit^-1, top 3 = 43.2%/43.3%):\n"
            "  1. Plastic bags size 1: 19.2%\n"
            "  2. Soft plastic fragments: 14.1%\n"
            "  3. Styrofoam food containers: 9.9%\n"
            "  4. Plastic strings, cords and ropes: 8.8%\n"
            "  5. Food wrappers: 7.7%\n"
            "  6. Other plastic: 6.2%\n"
            "  7. Fertilizer bags or containers: 4.8%\n"
            "  8. Crisp/Sweet packages: 4.2%\n"
            "  9. Fishing gear 2: 3.8%\n"
            "  10. Hard plastic fragments: 3.7%\n"
            "- Right Panel ('Non-tourist', axis 0–5 Item.unit^-1, top 3 = 44.4%):\n"
            "  1. Plastic bags size 1: 23.0%\n"
            "  2. Styrofoam food container: 11.9%\n"
            "  3. Soft plastic fragment: 9.5%\n"
            "  4. Food wrappers: 9.2%\n"
            "  5. Crisp/Sweet packages: 6.5%\n"
            "  6. Other wrappers: 5.2%\n"
            "  7. Hard plastic fragment: 5.0%\n"
            "  8. Plastic strings, cords and ropes: 4.5%\n"
            "  9. Other plastic: 4.1%\n"
            "  10. Fishing gear 2: 3.4%"
        ),
    },
    {
        "asset_id": "fig_17",
        "modality": "chart",
        "title": "Figure 17: Single-Use Plastic Waste by Density at River Sites in Surveyed Locations",
        "page": 47,
        "bbox": [0.11, 0.48, 0.89, 0.85],
        "section": "2.1.3.3 Results from the Surveys Conducted at River Sites",
        "content": (
            "[FIGURE 17 | chart | Page 47 | Section 2.1.3.3] Figure 17: Single-use Plastic Waste by Density at River Sites in Surveyed Locations (Grouped bar chart in Item.unit^-1, blue = Single use, green = Other).\n"
            "Exact Bar Values (Single use vs Other, in Item.unit^-1):\n"
            "- Can Tho: Single use = 24.9 | Other = 9.7\n"
            "- Da Nang: Single use = 8.9 | Other = 2.8\n"
            "- Hai Phong: Single use = 9.8 | Other = 3.0\n"
            "- Ho Chi Minh: Single use = 21.9 | Other = 11.5\n"
            "- Hue: Single use = 8.3 | Other = 2.1\n"
            "- Khanh Hoa: Single use = 5.8 | Other = 2.3\n"
            "- Lao Cai: Single use = 23.0 (22.9 in Table 24) | Other = 7.2 (7.15 in Table 24)\n"
            "- Phu Quoc: Single use = 7.0 | Other = 2.6\n"
            "- Quang Nam: Single use = 6.4 | Other = 3.0\n"
            "- Soc Trang: Single use = 4.0 | Other = 0.3\n"
            "Text above Figure 17 notes single-use plastic percentages at river sites ranged between 53% and 93% (highest in Soc Trang 93%, Hue 80%, Hai Phong 76%/77%, Da Nang 76%, Can Tho 72%)."
        ),
    },
    {
        "asset_id": "fig_18",
        "modality": "chart",
        "title": "Figure 18: Total Number of Waste Items (Percentage) on Surveyed Coastal Sites",
        "page": 48,
        "bbox": [0.16, 0.24, 0.84, 0.53],
        "section": "2.1.3.4 Results of the Survey Conducted at Coastal Sites",
        "content": (
            "[FIGURE 18 | chart | Page 48 | Section 2.1.3.4] Figure 18: Total Number of Waste Items (percentage) on Surveyed Coastal Sites (54 transects at 14 coastal sites in 8 locations: 21,749 pieces and 137 kg of debris collected).\n"
            "Pie Chart Values: Plastic = 95.4% | Other = 1.7% | Cloth/fabric = 1.3% | Glass = 0.9% | Mixed waste = 0.9%."
        ),
    },
    {
        "asset_id": "fig_19",
        "modality": "chart",
        "title": "Figure 19: Total Weight of Waste (Percentage) on Surveyed Ocean/Coastal Sites",
        "page": 48,
        "bbox": [0.16, 0.57, 0.84, 0.87],
        "section": "2.1.3.4 Results of the Survey Conducted at Coastal Sites",
        "content": (
            "[FIGURE 19 | chart | Page 48 | Section 2.1.3.4] Figure 19: Total Weight of Waste (percentage) on Surveyed Ocean Sites (137 kg total).\n"
            "Pie Chart Values: Plastic = 73.4% | Glass = 8.7% | Mix waste = 6.1% | Cloth/fabric = 4.6% | Rubber = 3.2% | Metal = 2.8% | Paper/timber = 1.3%."
        ),
    },
    {
        "asset_id": "fig_20",
        "modality": "chart",
        "title": "Figure 20: Total Density and Weight of Plastic Waste by Source on Surveyed Ocean Sites in Vietnam in 2020",
        "page": 49,
        "bbox": [0.22, 0.32, 0.78, 0.63],
        "section": "2.1.3.4 Results of the Survey Conducted at Coastal Sites",
        "content": (
            "[FIGURE 20 | chart | Page 49 | Section 2.1.3.4] Figure 20: Total Density and Weight of Plastic Waste by Source on Surveyed Ocean Sites in Vietnam in 2020 (Left axis: Item.unit^-1 0–35, blue bars = Density; Right axis: Gram.unit^-1 0–160, green dots = Weight).\n"
            "Exact Values by Source (chart labels vs exact text in paragraph above):\n"
            "1. Fisheries-related: Chart labels Density = 35% (text: 34.9%), Weight = 33% (text: 33.4%)\n"
            "2. Agriculture-related: Chart labels Density = 1%, Weight = 7%\n"
            "3. Take-away: Chart labels Density = 43% (text: 42.7%), Weight = 36% (text: 36.3%)\n"
            "4. Household: Chart labels Density = 20% (text: 20.4%), Weight = 22% (text: 21.9%)\n"
            "5. Medical-related: Chart labels Density = 1%, Weight = 1% (text: ~1% in number, ~7% combined with agriculture in weight)"
        ),
    },
    {
        "asset_id": "fig_21",
        "modality": "chart",
        "title": "Figure 21: Top 10 Plastic Waste Items (Standing Stock) at Coastal Sites",
        "page": 49,
        "bbox": [0.21, 0.65, 0.79, 0.92],
        "section": "2.1.3.4 Results of the Survey Conducted at Coastal Sites",
        "content": (
            "[FIGURE 21 | chart | Page 49 | Section 2.1.3.4] Figure 21: Top 10 Plastic Waste Items (Standing Stock) at Coastal Sites.\n"
            "Same standing-stock coastal series as Figure 3: 1. Fishing gear 1 (18.5% density, 19.1% weight); 2. Soft plastic fragments (18.1% density, 16.2% weight); 3. Fishing gear 2 (14.0% density, 12.8% weight); 4. Plastic bags size 1 (7.1% density, 8.3% weight); 5. Styrofoam food containers (6.8% density, 0.8% weight); 6. Hard plastic fragments (6.4% density, 3.8% weight); 7. Straws (4.9% density, 0.7% weight); 8. Other plastics (2.8% density, 11.7% weight); 9. Crisp/Sweet packages (2.8% density, 0.9% weight); 10. Other food wrappers (2.6% density, 1.0% weight). Total Top 10 = 84% of coastal standing stock density and 75.5% of weight."
        ),
    },
    {
        "asset_id": "fig_22",
        "modality": "chart",
        "title": "Figure 22: Top 10 Plastic Waste Items (Daily Accumulation) at Coastal Sites",
        "page": 50,
        "bbox": [0.16, 0.08, 0.84, 0.43],
        "section": "2.1.3.4 Results of the Survey Conducted at Coastal Sites",
        "content": (
            "[FIGURE 22 | chart | Page 50 | Section 2.1.3.4] Figure 22: Top 10 Plastic Waste Items (daily accumulation) at coastal sites (Left axis: items.m^-1 0–4.5, blue bars = Density; Right axis: gram.m^-1 0–18, grey dots = Weight).\n"
            "Exact Data Series (10 daily accumulation items left to right):\n"
            "1. Fishing gear 1: Density = 18.8% (~4.25 items.m^-1) | Weight = 18.7% (~16.2 gram.m^-1)\n"
            "2. Soft plastic fragments: Density = 17.6% (~3.98 items.m^-1) | Weight = 14.4% (~12.8 gram.m^-1)\n"
            "3. Styrofoam food containers: Density = 8.0% (~1.8 items.m^-1) | Weight = 1.1% (~1.0 gram.m^-1)\n"
            "4. Fishing gear 2: Density = 7.0% (~1.6 items.m^-1) | Weight = 9.1% (~8.0 gram.m^-1)\n"
            "5. Hard plastic fragments: Density = 6.6% (~1.5 items.m^-1) | Weight = 9.7% (~8.5 gram.m^-1)\n"
            "6. Plastic bags size 1: Density = 6.4% (~1.45 items.m^-1) | Weight = 11.5% (~10.1 gram.m^-1)\n"
            "7. Crisp/Sweet packages: Density = 6.2% (~1.4 items.m^-1) | Weight = 1.9% (~1.7 gram.m^-1)\n"
            "8. Plastic strings, cords and ropes: Density = 4.2% (~0.95 items.m^-1) | Weight = 1.9% (~1.7 gram.m^-1)\n"
            "9. Food wrappers: Density = 4.2% (~0.95 items.m^-1) | Weight = 2.5% (~2.2 gram.m^-1)\n"
            "10. Straws: Density = 3.8% (~0.85 items.m^-1) | Weight = 0.3% (~0.3 gram.m^-1)\n"
            "Text note on Page 50: Daily plastic debris accumulated at coastal sites accounted for 29.4% of the standing stock number."
        ),
    },
    {
        "asset_id": "fig_23",
        "modality": "chart",
        "title": "Figure 23: Single-Use Plastic Waste Density at Coastal Sites in Surveyed Locations",
        "page": 51,
        "bbox": [0.16, 0.53, 0.84, 0.83],
        "section": "2.1.3.4 Results of the Survey Conducted at Coastal Sites",
        "content": (
            "[FIGURE 23 | chart | Page 51 | Section 2.1.3.4] Figure 23: Single-use Plastic Waste Density at Coastal Sites in Surveyed Locations (Grouped bar chart, vertical axis 0.0–90.0 Item.unit^-1, blue bars = Single use, green bars = Other).\n"
            "Exact Bar Values across the 8 Coastal Locations (Single use vs Other, in Item.unit^-1):\n"
            "1. Da Nang: Single use = 10.5 | Other = 17.3 (Single-use share = 37.8% ~ 38%)\n"
            "2. Hai Phong: Single use = 15.4 | Other = 20.8 (Single-use share = 42.5%)\n"
            "3. Ho Chi Minh: Single use = 57.4 | Other = 78.5 (Highest Other plastic density at coastal sites = 78.5; Single-use share = 42.2%)\n"
            "4. Hue: Single use = 67.3 | Other = 73.8 (Single-use share = 47.7%)\n"
            "5. Khanh Hoa: Single use = 50.2 | Other = 30.6 (Single-use share = 62.1% ~ 62%)\n"
            "6. Phu Quoc: Single use = 34.4 | Other = 33.8 (Single-use share = 50.4% ~ 50%)\n"
            "7. Quang Nam: Single use = 70.1 | Other = 63.6 (Highest Single-use plastic density at coastal sites = 70.1; Single-use share = 52.4% ~ 52%)\n"
            "8. Soc Trang: Single use = 50.4 | Other = 29.6 (Single-use share = 63.0% ~ 63%, highest SUP % among coastal locations!)\n"
            "Overall at coastal sites, single-use plastics accounted for 52% of total plastic waste by number (ranging from 38% in Da Nang to 63% in Soc Trang)."
        ),
    },
    {
        "asset_id": "fig_28",
        "modality": "chart",
        "title": "Figure 28: Proportions of Waste Types in Hai Duong, Sapa, and Hai Phong, and Number of Items Combined (Drone Surveys)",
        "page": 67,
        "bbox": [0.08, 0.36, 0.92, 0.82],
        "section": "2.2.4.1 Results of the Drone Surveys",
        "content": (
            "[FIGURE 28 | chart | Page 67 | Section 2.2.4.1] Figure 28: Proportions of Waste Types in Hai Duong (A), Hai Phong (B), Sapa (C), and the Number of Items by Waste Type, Combined, in All Surveyed Cities (D).\n"
            "- Graph A (Pie chart 'Hai Duong'): Polystyrene = 43% | Cup lids, caps and small plastics = 21% | Other non-plastics = 12% | Wrappers = 7% | Bags robust PET = 5% | Bottles PET = 5% | Other plastics over 20cm = 4% | Bags LDPE = 3%.\n"
            "- Graph B (Pie chart 'Hai Phong'): Polystyrene = 30% | Bags LDPE = 26% | Other non-plastics = 20% | Bottles PET = 7% | Bags robust PET = 5% | Wrappers = 4% | Cup lids, caps and small plastics = 4% | Other plastics over 20cm = 4%.\n"
            "- Graph C (Pie chart 'Sapa'): Other non-plastics = 19% | Polystyrene = 18% | Cup lids, caps and small plastics = 18% | Bags LDPE = 17% | Bottles PET = 11% | Bags robust PET = 7% | Other plastics over 20cm = 6% | Wrappers = 2% | Rubber = 1% | Fishing gear = 1%.\n"
            "- Graph D (Horizontal bar chart 'All sites', axis 0 to 2,000 items): 1. Polystyrene (~1,858 items, 40%); 2. Cup lids, caps and small plastics (~886 items, 19%); 3. Other non-plastics (~580 items, 13%); followed by Bags LDPE (~287, 6%), Wrappers (~285, 6%), Bottles PET (~256, 6%), Bags robust PET (~233, 5%), Other plastics over 20cm (~204, 4%), and trace Fishing gear, Rubber, Metal."
        ),
    },
    {
        "asset_id": "fig_29",
        "modality": "chart",
        "title": "Figure 29: Waste Transport Over the Course of the Day for Hai Phong, Chanh Duong 02 Bridge",
        "page": 70,
        "bbox": [0.16, 0.08, 0.84, 0.38],
        "section": "2.2.4.2 Bridge Camera Results",
        "content": (
            "[FIGURE 29 | chart | Page 70 | Section 2.2.4.2] Figure 29: Waste transport over the course of the day for Hai Phong, Chanh Duong 02 bridge (Time-series line chart from 08:30 to 16:30 at 30-minute intervals, vertical axis 0–35 items, blue line = Camera 01, orange line = Camera 02).\n"
            "Key Trajectory Features:\n"
            "- Camera 01 (blue line): starts at 13 items (08:30), rises to 24 (09:00–09:30), dips to 20 (10:00), reaches the daily overall peak of 33 items at 10:30, drops to 26 (11:00) and 5 (11:30), rebounds to 16 (12:00), dips to 8 (12:30) and 7 (13:00), rises to 13 (13:30) and a second afternoon peak of 22 items at 14:00, then declines steadily (19 at 14:30, 16 at 15:00, 11 at 15:30, 6 at 16:00, 1 at 16:30).\n"
            "- Camera 02 (orange line): starts at 22 items (08:30), drops to 12 (09:00), 4 (09:30), and 1 (10:00), rises to 4 (10:30) and peaks at 25 items at 11:00, stays at 18 (11:30–12:00) and 20 (12:30), dips to 14 (13:00) and 11 (13:30), reaches an afternoon peak of 20 items at 14:00, then declines (13 at 14:30, 8 at 15:00–15:30, 2 at 16:00, 1 at 16:30)."
        ),
    },
    {
        "asset_id": "fig_30",
        "modality": "chart",
        "title": "Figure 30: Waste Classification by Quantity from Net Sampling at Chanh Duong 2",
        "page": 71,
        "bbox": [0.09, 0.08, 0.91, 0.44],
        "section": "2.2.4.3 Net Sampling Results",
        "content": (
            "[FIGURE 30 | chart | Page 71 | Section 2.2.4.3] Figure 30: Waste Classification by Quantity from Net Sampling at Chanh Duong 2 (Pie chart of 121 plastic pieces).\n"
            "Exact Pie Slice Shares:\n"
            "1. Packages and other wrapper: 41.32% (50 pieces)\n"
            "2. Plastic bag: 30.58% (37 pieces)\n"
            "3. Other plastic: 18.18% (22 pieces)\n"
            "4. Single use plastic product (cups, utensils): 3.31% (4 pieces)\n"
            "5. Beverage bottle: 2.48% (3 pieces)\n"
            "6. Bottle cap: 2.48% (3 pieces)\n"
            "7. Straws: 1.65% (2 pieces)"
        ),
    },
    {
        "asset_id": "fig_31",
        "modality": "chart",
        "title": "Figure 31: Waste Classification by Weight from Net Sampling at Chanh Duong 2",
        "page": 71,
        "bbox": [0.09, 0.48, 0.91, 0.83],
        "section": "2.2.4.3 Net Sampling Results",
        "content": (
            "[FIGURE 31 | chart | Page 71 | Section 2.2.4.3] Figure 31: Waste Classification by Weight from Net Sampling at Chanh Duong 2 ('Chart of waste classifition by weight in Chanh Duong 2', total 2,586 g).\n"
            "Exact Pie Slice Shares:\n"
            "1. Organic waste: 58% (1,500 g)\n"
            "2. Other plastic: 22% (571 g)\n"
            "3. Plastic bag: 15% (383 g)\n"
            "4. Packages and other wrapper: 3.41% (72 g)\n"
            "5. Beverage bottle: 1% (35 g)\n"
            "6. Single use plastic product (cups, utensils): 1% (35 g)"
        ),
    },
    {
        "asset_id": "fig_32",
        "modality": "chart",
        "title": "Figure 32: Top 10 Plastic Waste Items at Red River Sites",
        "page": 108,
        "bbox": [0.22, 0.19, 0.83, 0.50],
        "section": "Annex 2.1.C: Survey Results from River Sites",
        "content": (
            "[FIGURE 32 | chart | Page 108 | Annex 2.1.C] Figure 32: Top 10 Plastic Waste Items at Red River Sites (Lao Cai and Hai Phong; 20/28 plastic subcategories detected; Top 10 = 93.4% of total plastic waste; horizontal bar chart 0–12 items.unit^-1).\n"
            "Exact Ranking & Percentages:\n"
            "1. Plastic bags size 1: 44.7% (~10.9 items.unit^-1)\n"
            "2. Other food wrappers: 16.8% (~4.1 items.unit^-1)\n"
            "3. Plastic strings, cords and ropes: 9.7%\n"
            "4. Other plastic: 8.6%\n"
            "5. Crisp/Sweet packages: 3.6%\n"
            "6. Styrofoam food containers: 3.0%\n"
            "7. Hard plastic fragments: 2.2%\n"
            "8. Soft plastic fragments: 2.2%\n"
            "9. Bottle caps: 1.6%\n"
            "10. Straws: 1.4%"
        ),
    },
    {
        "asset_id": "fig_33",
        "modality": "chart",
        "title": "Figure 33: Top 10 Plastic Waste Items at Mekong River Sites",
        "page": 108,
        "bbox": [0.22, 0.58, 0.83, 0.90],
        "section": "Annex 2.1.C: Survey Results from River Sites",
        "content": (
            "[FIGURE 33 | chart | Page 108 | Annex 2.1.C] Figure 33: Top 10 Plastic Waste Items at Mekong River Sites (Can Tho and Soc Trang; 25/28 plastic categories detected; Top 10 = 81.5% of plastic waste; horizontal bar chart 0–5 items.unit^-1).\n"
            "Exact Ranking & Percentages:\n"
            "1. Styrofoam food container: 19.4% (~4.3 items.unit^-1)\n"
            "2. Plastic bags size 1: 11.9% (~2.65 items.unit^-1)\n"
            "3. Soft plastic fragments: 10.3% (~2.3 items.unit^-1)\n"
            "4. Hard plastic fragments: 6.6%\n"
            "5. Personal hygiene products: 6.4%\n"
            "6. Crisp/Sweet packages: 5.9%\n"
            "7. Food wrappers: 5.9%\n"
            "8. Other wrappers: 5.5%\n"
            "9. Plastic strings, cords and ropes: 5.3%\n"
            "10. Single use plastic product (cups, utensils): 4.1%"
        ),
    },
    {
        "asset_id": "fig_34",
        "modality": "chart",
        "title": "Figure 34: Top 10 Plastic Waste Items at Central Provinces River Sites",
        "page": 109,
        "bbox": [0.16, 0.12, 0.84, 0.49],
        "section": "Annex 2.1.C: Survey Results from River Sites",
        "content": (
            "[FIGURE 34 | chart | Page 109 | Annex 2.1.C] Figure 34: Top 10 Plastic Waste Items at Central Provinces River Sites (Hue, Quang Nam, Da Nang, Khanh Hoa; 22/28 subcategories detected; Top 10 = 86.2% of items; horizontal bar chart 0–3 items.unit^-1).\n"
            "Exact Ranking & Percentages:\n"
            "1. Soft plastic fragments: 25.9% (~2.5 items.unit^-1)\n"
            "2. Crisp/Sweet packages: 12.4%\n"
            "3. Other wrappers: 11.5%\n"
            "4. Plastic bags size 1: 9.9%\n"
            "5. Fertilizer bags or containers: 7.8%\n"
            "6. Hard plastic fragments: 4.6%\n"
            "7. Plastic bags size 2: 4.4%\n"
            "8. Other plastic: 3.4%\n"
            "9. Other food wrappers: 3.2%\n"
            "10. Plastic strings, cords and ropes: 3.2%"
        ),
    },
    {
        "asset_id": "fig_35",
        "modality": "chart",
        "title": "Figure 35: Top 10 Plastic Waste Items at Phu Quoc River Sites",
        "page": 109,
        "bbox": [0.16, 0.55, 0.84, 0.90],
        "section": "Annex 2.1.C: Survey Results from River Sites",
        "content": (
            "[FIGURE 35 | chart | Page 109 | Annex 2.1.C] Figure 35: Top 10 Plastic Waste Items at Phu Quoc River Sites (17/28 subcategories detected; Top 10 = 89.6% in density; horizontal bar chart 0–3.5 items.unit^-1).\n"
            "Exact Ranking & Percentages:\n"
            "1. Soft plastic fragments: 32.3% (~3.1 items.unit^-1)\n"
            "2. Fishing gear 2: 11.5% (~1.1 items.unit^-1)\n"
            "3. Plastic bags size 1: 9.4%\n"
            "4. Hard plastic fragments: 6.3%\n"
            "5. Plastic bags size 2: 6.3%\n"
            "6. Styrofoam food containers: 6.3%\n"
            "7. Crisp/Sweet packages: 5.2%\n"
            "8. Other food wrappers: 5.2%\n"
            "9. Fertilizer bags or containers: 4.2%\n"
            "10. Bottle caps: 3.1%"
        ),
    },
    {
        "asset_id": "fig_36",
        "modality": "chart",
        "title": "Figure 36: Top 10 Plastic Waste Items at Dong Nai-Sai Gon Riverbank Sites",
        "page": 110,
        "bbox": [0.16, 0.10, 0.84, 0.45],
        "section": "Annex 2.1.C: Survey Results from River Sites",
        "content": (
            "[FIGURE 36 | chart | Page 110 | Annex 2.1.C] Figure 36: Top 10 Plastic Waste Items at Dong Nai - Sai Gon Riverbank Sites (Ho Chi Minh City; 21/28 subcategories detected; Top 10 = 84.4% in number; horizontal bar chart 0–12 items.unit^-1).\n"
            "Exact Ranking & Percentages:\n"
            "1. Styrofoam food containers: 31.4% (~10.5 items.unit^-1)\n"
            "2. Fishing gear 2: 14.4% (~4.8 items.unit^-1)\n"
            "3. Plastic bags size 1: 8.4%\n"
            "4. Hard plastic fragments: 6.3%\n"
            "5. Straws: 6.3%\n"
            "6. Soft plastic fragments: 4.5%\n"
            "7. Food wrappers: 4.2%\n"
            "8. Other plastic: 3.3%\n"
            "9. Cigar tips: 3.0%\n"
            "10. Fertilizer bags or containers: 2.7%"
        ),
    },
    {
        "asset_id": "fig_37",
        "modality": "chart",
        "title": "Figure 37: Single-Use Plastic Waste Density at Each Riverbank Location",
        "page": 111,
        "bbox": [0.08, 0.08, 0.92, 0.38],
        "section": "Annex 2.1.C: Survey Results from River Sites",
        "content": (
            "[FIGURE 37 | chart | Page 111 | Annex 2.1.C] Figure 37: Single-use Plastic Waste Density at Each Riverbank Location (Grouped bar chart in Item.unit^-1 directly above Table 24; blue = Single use, teal = Other).\n"
            "Values match Figure 17 & Table 24: Can Tho (24.9 SUP, 9.7 Other), Da Nang (8.9, 2.8), Hai Phong (9.8, 3.0), Ho Chi Minh (21.9, 11.5), Hue (8.3, 2.1), Khanh Hoa (5.8, 2.3), Lao Cai (23.0 on chart / 22.9 in Table 24, 7.2 / 7.15 Other), Phu Quoc (7.0, 2.6), Quang Nam (6.4, 3.0), Soc Trang (4.0, 0.3)."
        ),
    },
    {
        "asset_id": "fig_38",
        "modality": "chart",
        "title": "Figure 38: Standing Stock and Daily Accumulation of Top 10 Plastic Waste Items on Coastal Sites in the Northern Subzone (Density)",
        "page": 112,
        "bbox": [0.18, 0.24, 0.91, 0.65],
        "section": "Annex 2.1.D: Survey Results for Coastal Sites",
        "content": (
            "[FIGURE 38 | chart | Page 112 | Annex 2.1.D] Figure 38: Standing Stock (blue bars) and 1-Day Accumulation (green bars) of the Top 10 Plastic Waste Items on Coastal Sites in the Northern Subzone (Hai Phong and Thua Thien Hue, density in items.m^-1, axis 0–18).\n"
            "Exact Values (Standing stock % vs 1 day accumulation %):\n"
            "1. Fishing gear 1: Fishing Plastic: Standing stock = 22.3% (~15.9 items.m^-1) | 1 day accumulation = 17.0% (~5.0 items.m^-1)\n"
            "2. Hard plastic fragment: Standing stock = 12.4% | 1 day accumulation = 10.8%\n"
            "3. Straws: Standing stock = 12.3% | 1 day accumulation = 7.5%\n"
            "4. Plastic bags size 1: Standing stock = 11.3% | 1 day accumulation = 9.4%\n"
            "5. Fishing gear 2: Polystyrenes-E: Standing stock = 10.5% | 1 day accumulation = 9.5%\n"
            "6. Soft plastic fragment: Standing stock = 7.7% | 1 day accumulation = 2.6%\n"
            "7. Crisp/Sweet packages: Standing stock = 3.7% | 1 day accumulation = 7.9%\n"
            "8. Other plastic: Standing stock = 3.7% | 1 day accumulation = 2.9%\n"
            "9. Plastic rope: Standing stock = 3.3% | 1 day accumulation = 8.7%\n"
            "10. Single use plastic product (PET): Standing stock = 2.6% | 1 day accumulation = 1.5%\n"
            "Note on Page 112: Styrofoam food containers were not even in the Top 10 in the Northern subzone (accounting for only 1.4%)."
        ),
    },
    {
        "asset_id": "fig_39",
        "modality": "chart",
        "title": "Figure 39: Standing Stock and Daily Accumulation of Top 10 Plastic Waste Items at Coastal Sites in the Transitional Subzone (Density)",
        "page": 113,
        "bbox": [0.14, 0.10, 0.86, 0.44],
        "section": "Annex 2.1.D: Survey Results for Coastal Sites",
        "content": (
            "[FIGURE 39 | chart | Page 113 | Annex 2.1.D] Figure 39: Standing Stock and Daily Accumulation of the Top 10 Plastic Waste Items at Coastal Sites in the Transitional Subzone (Da Nang, Quang Nam, Khanh Hoa; axis 0–20 items.m^-1).\n"
            "Exact Values (Standing stock % vs 1 day accumulation %):\n"
            "1. Soft plastic fragment: Standing stock = 21.7% (~15.5 items.m^-1) | 1 day accumulation = 20.3%\n"
            "2. Fishing gear 2: Polystyrenes-E: Standing stock = 15.8% | 1 day accumulation = 6.8%\n"
            "3. Fishing gear 1: Fishing Plastic: Standing stock = 15.7% | 1 day accumulation = 19.6%\n"
            "4. Plastic bags size 1: Standing stock = 6.8% | 1 day accumulation = 6.2%\n"
            "5. Plastic bags size 2: Standing stock = 5.8% | 1 day accumulation = 3.8%\n"
            "6. Styrofoam food container: Standing stock = 4.4% | 1 day accumulation = 4.6%\n"
            "7. Other plastic: Standing stock = 4.2% | 1 day accumulation = 1.2%\n"
            "8. Crisp/Sweet packages: Standing stock = 3.5% | 1 day accumulation = 8.3%\n"
            "9. Straws: Standing stock = 3.3% | 1 day accumulation = 3.2%\n"
            "10. Other food wrappers: Standing stock = 2.8% | 1 day accumulation = 4.9%"
        ),
    },
    {
        "asset_id": "fig_40",
        "modality": "chart",
        "title": "Figure 40: Standing Stock and Daily Accumulation of Top 10 Plastic Waste Items at Coastal Sites in the Southern Subzone (Density)",
        "page": 113,
        "bbox": [0.14, 0.48, 0.86, 0.86],
        "section": "Annex 2.1.D: Survey Results for Coastal Sites",
        "content": (
            "[FIGURE 40 | chart | Page 113 | Annex 2.1.D] Figure 40: Standing Stock and Daily Accumulation of the Top 10 Plastic Waste Items at Coastal Sites in the Southern Subzone (Ho Chi Minh City, Soc Trang, Phu Quoc; axis 0–20 items.m^-1).\n"
            "Exact Values (Standing stock % vs 1 day accumulation %):\n"
            "1. Soft plastic fragment: Standing stock = 19.9% (~17.2 items.m^-1) | 1 day accumulation = 28.0%\n"
            "2. Fishing gear 1: Fishing Plastic: Standing stock = 19.2% (~16.5 items.m^-1) | 1 day accumulation = 19.6%\n"
            "3. Fishing gear 2: Polystyrenes-E: Standing stock = 14.2% | 1 day accumulation = 5.0%\n"
            "4. Styrofoam food container: Standing stock = 11.7% (10.1% in text on p.50/112) | 1 day accumulation = 15.3%\n"
            "5. Hard plastic fragment: Standing stock = 6.7% | 1 day accumulation = 4.7%\n"
            "6. Plastic bags size 1: Standing stock = 5.4% | 1 day accumulation = 3.9%\n"
            "7. Other wrappers: Standing stock = 3.1% | 1 day accumulation = 3.8%\n"
            "8. Other food wrappers: Standing stock = 2.7% | 1 day accumulation = 2.0%\n"
            "9. Straws: Standing stock = 2.7% | 1 day accumulation = 1.3%\n"
            "10. Single use plastic product (PP): Standing stock = 2.2% | 1 day accumulation = 0.8%"
        ),
    },
    {
        "asset_id": "fig_41",
        "modality": "chart",
        "title": "Figure 41: Standing Stock and Daily Accumulation of Top 10 Plastic Waste Items at Rural Coastal Sites (Density)",
        "page": 114,
        "bbox": [0.21, 0.24, 0.79, 0.55],
        "section": "Annex 2.1.D: Survey Results for Coastal Sites",
        "content": (
            "[FIGURE 41 | chart | Page 114 | Annex 2.1.D] Figure 41: Standing Stock and Daily Accumulation of the Top 10 Plastic Waste Items at Rural Coastal Sites (Density, axis 0–24 items.m^-1; Top 10 = 84% in rural sites).\n"
            "Exact Values (Standing stock % vs 1 day accumulation %):\n"
            "1. Soft plastic fragment: Standing stock = 20.6% (~22.8 items.m^-1) | 1 day accumulation = 25.5%\n"
            "2. Fishing gear 2: Polystyrenes-E: Standing stock = 15.4% | 1 day accumulation = 4.1%\n"
            "3. Fishing gear 1: Fishing Plastic: Standing stock = 14.9% | 1 day accumulation = 20.9%\n"
            "4. Styrofoam food container: Standing stock = 8.0% | 1 day accumulation = 9.2%\n"
            "5. Plastic bags size 1: Standing stock = 6.9% | 1 day accumulation = 6.4%\n"
            "6. Hard plastic fragment: Standing stock = 5.1% | 1 day accumulation = 2.7%\n"
            "7. Plastic bags size 2: Standing stock = 3.4% | 1 day accumulation = 3.0%\n"
            "8. Straws: Standing stock = 3.3% | 1 day accumulation = 2.4%\n"
            "9. Other food wrappers: Standing stock = 3.3% | 1 day accumulation = 4.3%\n"
            "10. Other wrappers: Standing stock = 2.9% | 1 day accumulation = 4.7%"
        ),
    },
    {
        "asset_id": "fig_42",
        "modality": "chart",
        "title": "Figure 42: Standing Stock and Daily Accumulation of Top 10 Plastic Waste Items at Urban Coastal Sites (Density)",
        "page": 114,
        "bbox": [0.21, 0.58, 0.79, 0.90],
        "section": "Annex 2.1.D: Survey Results for Coastal Sites",
        "content": (
            "[FIGURE 42 | chart | Page 114 | Annex 2.1.D] Figure 42: Standing Stock and Daily Accumulation of Top 10 Plastic Waste Items at Urban Coastal Sites (Density, axis 0–14 items.m^-1; Top 10 = 87% in urban sites).\n"
            "Exact Values (Standing stock % vs 1 day accumulation %):\n"
            "1. Fishing gear 1: Fishing Plastic: Standing stock = 23.6% (~12.6 items.m^-1) | 1 day accumulation = 16.5%\n"
            "2. Soft plastic fragment: Standing stock = 14.4% | 1 day accumulation = 8.7%\n"
            "3. Fishing gear 2: Polystyrenes-E: Standing stock = 12.1% | 1 day accumulation = 10.2%\n"
            "4. Hard plastic fragment: Standing stock = 8.1% | 1 day accumulation = 11.0%\n"
            "5. Plastic bags size 1: Standing stock = 7.5% | 1 day accumulation = 6.4%\n"
            "6. Straws: Standing stock = 7.2% | 1 day accumulation = 5.4%\n"
            "7. Styrofoam food container: Standing stock = 5.2% | 1 day accumulation = 6.6%\n"
            "8. Crisp/Sweet packages: Standing stock = 3.4% | 1 day accumulation = 5.9%\n"
            "9. Other plastic: Standing stock = 2.8% | 1 day accumulation = 2.5%\n"
            "10. Plastic rope: Standing stock = 2.7% | 1 day accumulation = 6.8%"
        ),
    },
    {
        "asset_id": "fig_43",
        "modality": "chart",
        "title": "Figure 43: Standing Stock and Daily Accumulation of Top 10 Plastic Items at Non-Tourism Coastal Sites (Density)",
        "page": 115,
        "bbox": [0.18, 0.24, 0.82, 0.55],
        "section": "Annex 2.1.D: Survey Results for Coastal Sites",
        "content": (
            "[FIGURE 43 | chart | Page 115 | Annex 2.1.D] Figure 43: Standing Stock and Daily Accumulation of the Top 10 Plastic Items at Non-Tourism Coastal Sites (Density, axis 0–45 items.m^-1; Top 10 = 87% at non-tourism sites).\n"
            "Exact Values (Standing stock % vs 1 day accumulation %):\n"
            "1. Soft plastic fragment: Standing stock = 31.0% (~38.0 items.m^-1) | 1 day accumulation = 44.1%\n"
            "2. Fishing gear 1: Fishing Plastic: Standing stock = 18.6% | 1 day accumulation = 15.9%\n"
            "3. Fishing gear 2: Polystyrenes-E: Standing stock = 10.9% | 1 day accumulation = 3.6%\n"
            "4. Plastic bags size 1: Standing stock = 6.4% (Note: text on p.51/115 says 31% + 11.8% = 42.8% when combined with plastic bags size 1; chart bar label is 6.4%) | 1 day accumulation = 3.3%\n"
            "5. Plastic bags size 2: Standing stock = 5.4% | 1 day accumulation = 5.0%\n"
            "6. Hard plastic fragment: Standing stock = 3.5% | 1 day accumulation = 1.6%\n"
            "7. Crisp/Sweet packages: Standing stock = 3.0% | 1 day accumulation = 4.4%\n"
            "8. Styrofoam food container: Standing stock = 2.9% | 1 day accumulation = 2.6%\n"
            "9. Other food wrappers: Standing stock = 2.5% | 1 day accumulation = 2.7%\n"
            "10. Straws: Standing stock = 2.4% | 1 day accumulation = 2.3%"
        ),
    },
    {
        "asset_id": "fig_44",
        "modality": "chart",
        "title": "Figure 44: Standing Stock and Daily Accumulation of Top 10 Plastic Items at Tourism Coastal Sites (Density)",
        "page": 115,
        "bbox": [0.18, 0.59, 0.82, 0.90],
        "section": "Annex 2.1.D: Survey Results for Coastal Sites",
        "content": (
            "[FIGURE 44 | chart | Page 115 | Annex 2.1.D] Figure 44: The Standing Stock and Daily Accumulation of the Top 10 Plastic Items at Tourism Coastal Sites (Density, axis 0–12 items.m^-1; Top 10 = 85% at tourism sites).\n"
            "Exact Values (Standing stock % vs 1 day accumulation %):\n"
            "1. Fishing gear 1: Fishing Plastic: Standing stock = 18.4% (~11.2 items.m^-1) | 1 day accumulation = 20.0%\n"
            "2. Fishing gear 2: Polystyrenes-E: Standing stock = 16.2% (~9.8 items.m^-1) (Combined fishing gear 1 & 2 = 34.6%) | 1 day accumulation = 8.4%\n"
            "3. Styrofoam food container: Standing stock = 9.6% | 1 day accumulation = 10.2%\n"
            "4. Soft plastic fragment: Standing stock = 8.9% | 1 day accumulation = 6.6%\n"
            "5. Hard plastic fragment: Standing stock = 8.4% | 1 day accumulation = 8.7%\n"
            "6. Plastic bags size 1: Standing stock = 7.7% | 1 day accumulation = 7.6%\n"
            "7. Straws: Standing stock = 6.7% | 1 day accumulation = 4.5%\n"
            "8. Other plastic: Standing stock = 4.1% | 1 day accumulation = 1.9%\n"
            "9. Plastic rope: Standing stock = 2.7% | 1 day accumulation = 4.9%\n"
            "10. Crisp/Sweet packages: Standing stock = 2.6% | 1 day accumulation = 7.0%"
        ),
    },
    {
        "asset_id": "fig_50",
        "modality": "chart",
        "title": "Figure 50: Example of Multi-Point Plastic Concentration and Flow Velocity Profile in the Danube River Near Hainburg",
        "page": 122,
        "bbox": [0.08, 0.08, 0.92, 0.43],
        "section": "Annex 2.2.A: Plastic Flow Calculations and Modelling",
        "content": (
            "[FIGURE 50 | chart | Page 122 | Annex 2.2.A] Figure 50: Example of the data gathered for one multi-point measurement performed in the Danube River near Hainburg (13 January 2015, Liedermann et al., 2018).\n"
            "Chart Axes & Legend:\n"
            "- Horizontal axis: 'Width [m]' from 800 m (left bank) to 400 m (right bank), with 'Measuring bridge' pier indicated near 635 m.\n"
            "- Left vertical axis: 'Elevation [m a.s.l.]' from 135 to 146 m a.s.l. (water surface at ~140.5 m a.s.l.).\n"
            "- Right vertical axis: 'Flow velocity [m/s]' from -3 to +2.5 m/s (red curve above water surface plots surface/cross-sectional flow velocity peaking around 2.0–2.2 m/s).\n"
            "- Top-right label: 'Discharge: 3392 m3/s' (3.392 m3 s^-1 in note).\n"
            "- Color-coded markers at 7 vertical profiles across the river width show 'Plastic concentration [mg/1000m3]' for 500 um squares (left number) and 250 um triangles (right number): e.g. surface profile points from left to right: (2103, 6366), (1089, 2597), (569, 664), (226, 242), (258, 481), (859, 1296), (956, 6610); mid-depth points: (923, 336), (457, 539), (1473, 642), (462, 703), (329, 205), (209, 233), (833, 281); near-bed points: 359, 292, 450, 514, 55, 170, 943.\n"
            "- Equation (2) below Figure 50: Transport rate q_{i,j} [g m^-2 s^-1] = C_{i,j} [g m^-3] * v_{i,j} [m s^-1]. Hydrodynamic 3D numerical model used by BOKU/IWA is 'R-Sim3D' (Tritthart and Gutknecht, 2007) solving Reynolds-averaged Navier-Stokes equations with k-epsilon and k-omega turbulence closure."
        ),
    },
]


def _render_crop(doc: pymupdf.Document, page_number: int, bbox: list[float], out_path: Path, dpi: int = 160) -> None:
    """Render a normalized bounding-box [x0, y0, x1, y1] from 1-based page_number to PNG."""
    page = doc[page_number - 1]
    rect = page.rect
    clip = pymupdf.Rect(
        rect.x0 + bbox[0] * rect.width,
        rect.y0 + bbox[1] * rect.height,
        rect.x0 + bbox[2] * rect.width,
        rect.y0 + bbox[3] * rect.height,
    )
    pix = page.get_pixmap(dpi=dpi, clip=clip)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(out_path))


def _clean_page_text(raw: str) -> str:
    """Normalize PDF page text while preserving paragraph boundaries."""
    lines = [line.strip() for line in raw.replace("\r", "\n").split("\n")]
    cleaned: list[str] = []
    for line in lines:
        if not line:
            cleaned.append("")
            continue
        # Skip standalone page numbers / running headers
        if re.match(r"^(\d+\s*\|\s*Vietnam:\s*Plastic\s*Pollution\s*Diagnostics|Vietnam:\s*Plastic\s*Pollution\s*Diagnostics\s*\|\s*\d+)$", line, re.I):
            continue
        cleaned.append(line)
    text = "\n".join(cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build_bonus_chunks(pdf_path: Path = BONUS_PDF_PATH, crops_dir: Path = BONUS_CROPS_DIR) -> tuple[list[day6.Chunk], dict[str, Any]]:
    """Extract multimodal chunks (text, table, image_diagram, chart) with bbox metadata."""
    if not pdf_path.exists():
        raise FileNotFoundError(f"Bonus PDF not found at {pdf_path}")

    doc = pymupdf.open(str(pdf_path))
    total_pages = len(doc)

    chunks: list[day6.Chunk] = []
    source_meta = dict(BONUS_SOURCE_META)
    blank_page_nums = {b["page"] for b in BLANK_PAGES}

    # 1. Extract text chunks across all 137 non-blank pages
    current_section = "Front Matter"
    text_pages_processed = 0
    for pno in range(1, total_pages + 1):
        if pno in blank_page_nums:
            continue
        raw_text = doc[pno - 1].get_text("text")
        cleaned = _clean_page_text(raw_text)
        if not cleaned:
            continue
        text_pages_processed += 1

        # Detect section heading updates
        for line in cleaned.split("\n")[:6]:
            if re.match(r"^(EXECUTIVE SUMMARY|1\.\s*INTRODUCTION|2\.1\b|2\.2\b|2\.3\b|3\.\s*POLICY|ANNEX\s+2\.)", line, re.I):
                current_section = line[:90]
                break

        page_obj = day6.DocumentPage(
            document_id=BONUS_SOURCE_ID,
            source=BONUS_SOURCE_URL,
            page=pno,
            text=cleaned,
            metadata={
                **source_meta,
                "section": current_section,
                "modality": "text",
                "asset_id": None,
                "crop_path": None,
                "bbox": None,
            },
        )
        page_chunks = day6.by_paragraph(page_obj, max_size=900, strategy_label=BONUS_STRATEGY)
        for idx, ch in enumerate(page_chunks):
            if len(ch.text.strip()) < 25:
                continue
            chunk_id = f"BONUS__{BONUS_SOURCE_ID}__p{pno:03d}__t{idx:02d}"
            full_text = f"[Page {pno} | {current_section}] {ch.text.strip()}"
            meta = dict(ch.metadata)
            meta["char_length"] = len(full_text)
            chunks.append(
                day6.Chunk(
                    chunk_id=chunk_id,
                    document_id=BONUS_SOURCE_ID,
                    source=BONUS_SOURCE_URL,
                    page=pno,
                    text=full_text,
                    metadata=meta,
                )
            )

    # 2. Extract all 26 numbered tables
    for idx, tbl in enumerate(VERIFIED_TABLES):
        asset_id = tbl["asset_id"]
        chunk_id = f"BONUS__{BONUS_SOURCE_ID}__p{tbl['page']:03d}__{asset_id}"
        meta = {
            **source_meta,
            "document_id": BONUS_SOURCE_ID,
            "source": BONUS_SOURCE_URL,
            "page": tbl["page"],
            "chunk_strategy": BONUS_STRATEGY,
            "char_length": len(tbl["content"]),
            "section": tbl["section"],
            "modality": "table",
            "asset_id": asset_id,
            "title": tbl["title"],
            "crop_path": None,
            "bbox": tbl["bbox"],
        }
        chunks.append(
            day6.Chunk(
                chunk_id=chunk_id,
                document_id=BONUS_SOURCE_ID,
                source=BONUS_SOURCE_URL,
                page=tbl["page"],
                text=tbl["content"],
                metadata=meta,
            )
        )

    # 3. Extract all 54 numbered figures (16 image_diagram + 38 chart)
    for idx, fig in enumerate(VERIFIED_FIGURES):
        asset_id = fig["asset_id"]
        chunk_id = f"BONUS__{BONUS_SOURCE_ID}__p{fig['page']:03d}__{asset_id}"
        meta = {
            **source_meta,
            "document_id": BONUS_SOURCE_ID,
            "source": BONUS_SOURCE_URL,
            "page": fig["page"],
            "chunk_strategy": BONUS_STRATEGY,
            "char_length": len(fig["content"]),
            "section": fig["section"],
            "modality": fig["modality"],
            "asset_id": asset_id,
            "title": fig["title"],
            "crop_path": None,
            "bbox": fig["bbox"],
        }
        chunks.append(
            day6.Chunk(
                chunk_id=chunk_id,
                document_id=BONUS_SOURCE_ID,
                source=BONUS_SOURCE_URL,
                page=fig["page"],
                text=fig["content"],
                metadata=meta,
            )
        )

    doc.close()

    modality_counts: dict[str, int] = {}
    for ch in chunks:
        mod = ch.metadata["modality"]
        modality_counts[mod] = modality_counts.get(mod, 0) + 1

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "index_strategy": BONUS_STRATEGY,
        "document": {
            **source_meta,
            "local_pdf_path": "data/bonus/wb_vietnam_plastic_2022.pdf",
            "total_pages": total_pages,
            "processed_text_pages": text_pages_processed,
            "blank_pages_skipped": BLANK_PAGES,
            "decorative_pages_logged": DECORATIVE_PAGES,
        },
        "total_chunks": len(chunks),
        "modality_counts": modality_counts,
        "table_assets_count": len(VERIFIED_TABLES),
        "figure_assets_count": len(VERIFIED_FIGURES),
    }
    return chunks, manifest


def ingest_bonus_corpus() -> dict[str, Any]:
    """Build chunks, embed with BAAI/bge-base-en-v1.5, and upsert into pgvector (strategy='BONUS')."""
    t0 = time.perf_counter()
    chunks, manifest = build_bonus_chunks()

    embedder = day6.build_embedder(provider=day6.EMBEDDING_PROVIDER, model_name=day6.EMBEDDING_MODEL)
    t1 = time.perf_counter()
    vectors = embedder.embed_documents([c.text for c in chunks])
    embed_s = time.perf_counter() - t1

    store = day6.PgVectorStore(day6.DATABASE_URL, dimensions=embedder.dimensions)
    store.create_schema()
    upsert_res = store.upsert(BONUS_STRATEGY, chunks, vectors)
    stored = store.count_chunks(BONUS_STRATEGY)

    out_records = [
        {
            "id": c.chunk_id,
            "text": c.text,
            "source_id": c.document_id,
            "source": c.source,
            "page": c.page,
            "metadata": c.metadata,
        }
        for c in chunks
    ]
    BONUS_CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(out_records, ensure_ascii=False, indent=1)
    BONUS_CHUNKS_PATH.write_text(blob, encoding="utf-8")

    manifest.update(
        {
            "stored_rows": stored,
            "embedding_provider": day6.EMBEDDING_PROVIDER,
            "embedding_model": day6.EMBEDDING_MODEL,
            "dimensions": embedder.dimensions,
            "vector_store": "PostgreSQL + pgvector (exact cosine, Day 6 docker-compose)",
            "chunks_sha256": hashlib.sha256(blob.encode("utf-8")).hexdigest(),
            "upsert": upsert_res,
            "embed_seconds": round(embed_s, 2),
            "total_seconds": round(time.perf_counter() - t0, 2),
        }
    )
    BONUS_MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if stored != len(chunks):
        raise RuntimeError(f"store has {stored} rows for BONUS but {len(chunks)} chunks were built")
    return manifest


if __name__ == "__main__":
    summary = ingest_bonus_corpus()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
