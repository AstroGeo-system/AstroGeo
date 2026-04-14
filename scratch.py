ASTROGEO
UI Bug Fix & Feature Implementation Plan
Based on Live Screenshot Review — April 2026


Master Issue Summary

#
Page
Issue
Severity
Est. Fix Time
1
Research Lab
Model Cards show empty Training Data and Benchmark fields
HIGH
1-2 hrs
2
Research Lab
View Full Model Card PDF button does nothing / 404
HIGH
1-2 hrs
3
Research Lab
Verify Predictions tab — predictions not showing
CRITICAL
2-3 hrs
4
Astronomy
Satellite Pass Predictor returns HTML instead of JSON
CRITICAL
1-2 hrs
5
Astronomy
Launch countdown shows 0d 0h 0m 0s — launch already passed
HIGH
1 hr
6
Astronomy
Starlink appearing in ISRO-only filtered launch schedule
MEDIUM
30 min
7
Astronomy
Launch AI Prediction missing SHAP breakdown card
HIGH
2-3 hrs
8
Earth
NDVI map only highlights Maharashtra, all other states invisible
CRITICAL
2-3 hrs
9
Earth
Total Δ NDVI field shows — (empty)
HIGH
1 hr
10
Earth
Zone breakdown labels run together with no spacing
MEDIUM
30 min

Note: Severity CRITICAL means the feature is completely non-functional and will fail during any demo or evaluation. Fix these before anything else.

Page: Research Lab — Model Cards

Bug 1: Empty Training Data and Benchmark fields    HIGH 

What you see
All three model cards (Asteroid Anomaly Detection, Asteroid Behavioural Clustering, Vegetation Change Detection) show a dash (—) under both the TRAINING DATA and LATEST BENCHMARK labels. The green dot next to each card title suggests the backend is reachable, but the data fields are not populated.

Root cause
The frontend component that renders each model card is fetching from /api/verify/model-cards (or equivalent) and receiving a response, but the fields it is looking for in the JSON have either a different key name than expected, are null, or are nested differently than the component expects. The green dot means the API call succeeded — but the field mapping is wrong.

Diagnosis steps
	•	Open browser developer tools, go to the Network tab, navigate to Research Lab and click Model Cards.
	•	Find the API call that fetches model card data. Click on it and look at the Response body.
	•	Check the exact JSON keys returned. For example, the API might return training_dataset but the frontend is looking for trainingData or training_data.
	•	Compare the key names in the API response to the key names used in the frontend component that renders Training Data and Latest Benchmark.

Fix
There are two equally valid fixes depending on where you prefer to make the change:
	•	Option A (preferred): Update the frontend component to use the exact key names returned by the API. No backend change needed.
	•	Option B: Update the backend to return the keys the frontend expects. Requires redeployment of the backend.

What the model cards should display after fix:

Card
Training Data field
Latest Benchmark field
Asteroid Anomaly Detection
NASA CNEOS 1900–2200, 5,836 records, 9 engineered features
Isolation Forest, contamination=5%, top SHAP: kinetic_energy_proxy
Asteroid Behavioural Clustering
NASA CNEOS close-approach data, 3 clusters
KMeans k=3, top cluster driver: distance_trend
Vegetation Change Detection
Sentinel-2 NDVI composites, 17 Indian zones, 2018–2024
Random Forest, 82% test accuracy, 77.9% 5-fold CV

Note: If these values are not currently being returned by the backend at all, they need to be hardcoded into the model card API response objects. They are static facts about your models — they do not need to be computed at runtime.



Bug 2: View Full Model Card PDF button non-functional    HIGH 

What you see
Clicking 'View Full Model Card PDF' on any of the three cards either does nothing, opens a blank tab, or returns a 404 error.

Root cause — three possibilities
	•	The PDF files do not exist at the path the frontend is pointing to. Check if the PDF files are actually present in your public/ or static/ folder.
	•	The /api/verify/model-cards endpoint is supposed to return a URL or a file path to the PDF, but it is returning null or an incorrect path.
	•	The button click handler has an error — it may be calling window.open(undefined) which opens a blank tab.

Fix
	•	Check if model card PDF files actually exist anywhere in your project. If they do not, you have two options: generate them (see below) or replace the button with a 'View Details' button that opens a modal with the card data inline instead of a PDF.
	•	If PDFs exist, confirm the file path matches what the button is using. The path should be absolute from the public root.
	•	If PDFs do not exist and you want to generate them quickly: the model card content is already in your API response. Create a simple PDF from each card's JSON data using a backend PDF generation library. The content for each card is already fully specified in the table above.

Recommended quick fix for demo:
Replace the 'View Full Model Card PDF' button with a 'View Model Card' button that opens an in-page modal or drawer containing the model card information formatted as a readable card. This avoids the PDF generation complexity entirely and looks cleaner on screen. The modal should show: Model Name, Version, Architecture Domain, Training Data details, Feature List, Performance Metrics (accuracy, CV score, ROC-AUC), SHAP top features, Intended Use, and Known Limitations.

Page: Research Lab — Verify Predictions Tab

Bug 3: Predictions not showing in Verify Predictions tab    CRITICAL 

What you see
The Verify Predictions tab loads but shows no predictions. The audit log or prediction list is empty. This makes the SHA-256 tamper detection feature — one of AstroGeo's core responsible AI claims — completely undemonstrable.

Diagnosis — work through these in order

Step 1: Check the API endpoint directly
In your browser, navigate directly to your backend URL followed by /api/verify/batch/recent. For example: http://localhost:8000/api/verify/batch/recent or https://your-deployed-backend.com/api/verify/batch/recent.
	•	If this returns a JSON array of predictions: the backend is fine, the problem is in the frontend fetch call or state management.
	•	If this returns an empty array []: the predictions are not in the database — see Step 2.
	•	If this returns an HTML error page: the route is not registered — see Step 3.
	•	If this returns a CORS error in the browser: see Step 4.

Step 2: If the database is empty
Your prediction generation pipeline should have stored 5,836 asteroid predictions with their SHA-256 hashes when the Isolation Forest model was run. If the database is empty, the pipeline either did not write to the database, wrote to a different table or collection, or wrote to a local file instead of the database.
	•	Check your Isolation Forest prediction script — look for where it saves results. It may be writing to a CSV file rather than inserting into your database.
	•	If predictions are in a CSV file, run a one-time migration script to insert all rows into your database table with their pre-computed SHA-256 hashes.
	•	Confirm the database table name matches what the /api/verify/batch/recent route is querying.

Step 3: If the route returns a 404
The verify router is not registered in your FastAPI application. Open your main.py (or app.py) and check that the verify router is imported and added with app.include_router(). If the import exists but the route still 404s, check that the route prefix is correct — it should be /api/verify, not /verify or /api/v1/verify.

Step 4: If there is a CORS error
Your FastAPI CORS middleware is not allowing requests from your frontend origin. In your main.py, find the CORSMiddleware configuration and ensure allow_origins includes both http://localhost:3000 and your deployed frontend domain. If you are unsure, temporarily set allow_origins to ["*"] to confirm CORS is the issue, then restrict it properly before deployment.

What the fixed Verify Predictions tab must show
	•	A text input where the user can type an asteroid designation (e.g. 2024 YR4) and click Verify.
	•	On clicking Verify, the tab calls /api/verify/{designation} and shows either a green VERIFIED banner or a red INTEGRITY FAILURE banner with the hash value displayed.
	•	A table below the input showing the last 10 verified predictions from /api/verify/batch/recent. Columns: Designation, Risk Category, Anomaly Score (to 4 decimal places), Hash (first 16 characters followed by ...), Status (VERIFIED in green).
	•	A summary row at the bottom: Total predictions in system: 5,836 | Hash algorithm: SHA-256 | Salt: astrogeo-asteroid-v1.0.

⚠ This feature is cited in your paper as a key responsible AI contribution. If it does not work during evaluation, it undermines the entire cryptographic auditability claim. Treat this as the highest priority fix on this page.

Page: Astronomy — Satellite Pass Predictor

Bug 4: Error — Unexpected token '<', <!DOCTYPE... is not valid JSON    CRITICAL 

What you see
After clicking Find Passes with ISS selected and Mumbai, MH as the location, the Upcoming Visible Passes section shows the error: 'Error: Unexpected token <, <!DOCTYPE ... is not valid JSON'.

What this error means
This error always means one thing: the frontend made an API call expecting to receive JSON, but received an HTML document instead. HTML documents start with <!DOCTYPE html>, which begins with the < character — hence the 'unexpected token <' message. The browser's JSON parser cannot parse HTML and throws this error.

An API endpoint returns HTML instead of JSON in exactly two situations: the endpoint does not exist (the web server returns its default 404 HTML page), or the endpoint threw an unhandled server error (the server returns its default 500 error HTML page).

Diagnosis steps
	•	Open browser developer tools, go to the Network tab, click Find Passes.
	•	Find the failing request. It will be red. Click on it.
	•	Check the URL it is calling. Is it calling your FastAPI backend URL, or is it calling a Next.js API route at /api/v1/iss/passes?
	•	Check the Status code. 404 means the route does not exist. 500 means the route exists but threw an error.
	•	If status is 500: go to your backend terminal or logs and find the full Python traceback. The error will be clearly described there.

Most likely root cause
The N2YO API call inside your /api/v1/iss/passes backend route is failing. The most common reasons are:
	•	The N2YO API key is not set in the backend environment variables, or it has expired. N2YO free-tier keys have rate limits and can be suspended.
	•	The N2YO API is being called with the wrong parameters. Check the NORAD ID being passed — ISS is NORAD ID 25544. If the ID is wrong or missing, N2YO returns an error page.
	•	The observer latitude and longitude for Mumbai are missing or malformed. N2YO requires lat, lon, and altitude (in metres) as query parameters.
	•	The N2YO response itself is not valid JSON — N2YO occasionally returns error strings rather than JSON objects on invalid requests.

Fix
	•	Test your N2YO API key directly by opening this URL in your browser (replace YOUR_KEY): https://api.n2yo.com/rest/v1/satellite/radiopasses/25544/19.076/72.877/14/7/10/&apiKey=YOUR_KEY. If this returns JSON, the key works. If it returns an error, the key is the problem.
	•	Add proper error handling in your backend route: wrap the N2YO API call in a try-except block. If N2YO returns an error, your endpoint should return a JSON error response like {"error": "N2YO API unavailable", "detail": "..."} with a 503 status code — not let the exception propagate to an HTML 500 page.
	•	On the frontend, check for the error field in the response and display a user-friendly message like 'Satellite pass data temporarily unavailable. Please check your N2YO API key.' instead of the raw JSON parse error.

Note: Mumbai coordinates for N2YO: latitude 19.0760, longitude 72.8777, altitude 14 metres. Sriharikota coordinates (for ISRO context): latitude 13.7200, longitude 80.2300, altitude 5 metres.

Page: Astronomy — Launches Tab

Bug 5: Launch countdown shows 0d 0h 0m 0s    HIGH 

What you see
The NEXT ISRO LAUNCH card shows PSLV-C59 / PROBA-3 with the countdown at exactly 0 days, 0 hours, 0 minutes, 0 seconds. This mission has already launched — PSLV-C59 / PROBA-3 launched in December 2024.

Root cause
The next upcoming launch is hardcoded or fetched from a data source that has not been updated since December 2024. The countdown is computed as (launch_date - now), which is now a negative number. The component is either clamping to zero rather than showing a negative countdown, or it is not recognising that this launch has already occurred and moving to the next mission.

Fix
	•	Update the launch data source. If the next launch is hardcoded in the frontend or in a backend configuration file, change it to a current upcoming ISRO launch. As of April 2026, upcoming missions include Gaganyaan G1 (uncrewed orbital test), GISAT-1A, and Chandrayaan-4 preparatory launches. Check the ISRO official website or rocketlaunch.org/launch-schedule/indian-space-research-organization for the current next launch date.
	•	Fix the countdown logic: the component should filter the launch list to only those with launch_date > now before selecting the 'next' launch. If the filtered list is empty, show 'No upcoming launches scheduled — check ISRO website for updates' rather than a zeroed-out countdown.
	•	If launch data is fetched from a third-party API like The Space Devs Launch Library (ll.thespacedevs.com), check that the API call is including the filter is_crewed=false&lsp__name=ISRO&net__gte=now to return only future ISRO launches.



Bug 6: Starlink appearing in ISRO-only launch schedule    MEDIUM 

What you see
In the Global Launch Schedule panel, the ISRO checkbox is ticked and SpaceX, NASA, Others are unticked. Yet the schedule shows 'Starlink Group 7-14' from SpaceX on February 1st alongside the ISRO 'NGLV Test Flight' on February 10th.

Root cause
The filter logic is not being applied correctly on the frontend. The checkbox state is being tracked but the filter is either not being applied to the data array before rendering, or it is being applied using the wrong field. The SpaceX entry is slipping through because the filter condition has a bug.

Fix
	•	Find the component that renders the launch schedule list. Locate where the checkbox state (selectedAgencies) is defined.
	•	Find where the launch data array is rendered into list items. Add a filter step before the .map() call: filter the array to only include launches where the agency field matches one of the selected checkboxes.
	•	Check the exact value of the agency field in your launch data objects — it might be 'SpaceX', 'SPACEX', 'spacex', or an agency ID number. The filter comparison must match the exact field value. Use case-insensitive comparison to be safe.
	•	Edge case: if 'All Agencies' is checked, show everything regardless of other checkboxes. If 'All Agencies' is unchecked, show only missions from the ticked agencies.



Bug 7: Launch AI Prediction missing SHAP breakdown    HIGH 

What you see
The AI PREDICTION card shows 76% probability and basic weather data (Risk Level: Favorable, Temperature: 29.7°C, Humidity: 85%, Wind Speed: 4.2 m/s) but has no SHAP feature breakdown showing WHY the model gave 76%. This is the most important explainability element in the platform.

What needs to be added
Directly below the existing weather fields, add a section titled 'MODEL EXPLANATION — What’s Driving This?' containing the following elements:

	•	A horizontal bar chart showing the top 4 SHAP feature contributions. Each bar has: a label (Precipitation, Monsoon Season, Cloud Cover, Wind Speed), a bar whose width is proportional to the absolute SHAP value, a colour (orange-red if it increases risk, green if it decreases risk), and a signed value on the right (+0.23, -0.08 etc.).
	•	One auto-generated plain-language sentence below the bars. The sentence is constructed from the top two features: if the top feature increases risk, start with 'Primary risk factor: [feature name] is currently [value] — above safe launch threshold.' If it decreases risk, start with 'Conditions are favourable: [feature name] is within normal range.'
	•	A Solar Communication Risk chip: a colour-coded badge showing days since last X-class flare. Green for 4+ days (NOMINAL), amber for 2-3 days (ELEVATED), red for 0-1 days (ACTIVE RISK). This is fetched from your new /api/launch/solar-risk endpoint.

Backend requirement
Confirm that /api/launch/probability already returns a shap_contributions field in its JSON response. If it does not, the backend developer needs to add it — the SHAP values are already computed during model inference via the SHAP library, they just need to be serialised into the API response as an array of objects with the shape: {feature_name: string, contribution: float, direction: 'increases_risk' | 'decreases_risk'}.

Page: Earth — Vegetation / NDVI Map

Bug 8: Map only shows Maharashtra — all other states invisible    CRITICAL 

What you see
The NDVI Vegetation Health Monitoring map shows India with Maharashtra highlighted in yellow-amber (indicating Moderate NDVI). All other states appear in the same dark blue as the ocean — they have no highlighting, no NDVI colour, and appear non-existent. The dropdown shows Maharashtra is selected.

Root cause — two likely causes

Cause A: The map only renders the selected state, not all states
The most likely cause is that the map component is designed to highlight only the currently selected state from the dropdown, rather than showing all states simultaneously with their respective NDVI colours. When Maharashtra is selected, only Maharashtra gets a colour fill. All other states get the default dark fill which blends into the basemap.

This is a design decision problem, not a data problem. The fix is to change the map rendering logic from 'colour only the selected state' to 'colour all states using their NDVI value, and outline or bold the selected state to indicate selection.'

Cause B: The GeoJSON layer only has Maharashtra polygon data
The GeoJSON file being used for the Indian states layer may only contain the Maharashtra polygon. If the other 27 state polygons are missing from the GeoJSON, they cannot be rendered. Check the GeoJSON file size — a complete India states GeoJSON with all 28 states should be at least 1-2 MB. If it is very small (under 200 KB), it likely only contains one or a few states.

Fix for Cause A (most likely)
	•	The map component should fetch NDVI data for ALL zones on page load — not just the selected state. Call /api/earth/ndvi for all 17 zones and store the results.
	•	When rendering the GeoJSON layer, apply a colour fill to every state polygon based on its NDVI value using the legend thresholds: green for NDVI > 0.6 (Healthy), amber for 0.3-0.6 (Moderate), red for NDVI < 0.3 (Poor).
	•	For states where you have no NDVI data, apply a neutral grey fill — never the same dark colour as the ocean, which makes them invisible.
	•	When a state is selected from the dropdown, increase its border weight and show its detailed data in the right panel — but do not change its fill colour from the NDVI-based colour.

Fix for Cause B (if GeoJSON is incomplete)
Download a complete India states GeoJSON from a reliable source such as the Datameet India Maps repository on GitHub (github.com/datameet/maps) or the GADM database (gadm.org). Replace your current GeoJSON file with the complete version. The state name field in the GeoJSON must match the zone names used in your NDVI API responses — check and align these before rendering.

Note: A map of India that only shows one state on the Earth Observatory page is one of the most visually jarring issues in the entire platform. Evaluators looking at the screen will notice immediately. This must be fixed before any presentation.



Bug 9: Total Δ NDVI field shows empty dash    HIGH 

What you see
In the AI-DETECTED CHANGES panel on the right, the 'Total Δ NDVI' field shows a dash (—) while 'Zones Analysed' correctly shows 2. The NDVI Mean shows 0.362 which is a real value. The Δ NDVI (delta) value is missing.

Root cause
The Total Δ NDVI value requires a comparison between two time periods — for example, the NDVI mean in 2024 versus the NDVI mean in 2022 (a two-year baseline). This comparison either: is not being computed by the backend and the field is genuinely null in the API response, or is being returned as null because the historical baseline data for the selected zones is missing, or the frontend is expecting a field named ndvi_delta but the API returns ndvi_change or delta_ndvi.

Fix
	•	Check the API response for /api/earth/change/{zone} or /api/earth/ndvi/{zone}. Look for any field containing 'delta', 'change', or 'diff' in its name. If such a field exists but is null, the baseline data is missing.
	•	If the delta field is missing entirely from the API response, it needs to be added: compute it as (current_year_ndvi_mean - baseline_ndvi_mean) where baseline is the 3-year average from 2019-2021.
	•	If the field exists but has a different name than the frontend expects, update the frontend to use the correct field name.
	•	The displayed value should be a signed decimal with 3 decimal places and a sign indicator: for example, δ NDVI: -0.087 (shown in red, indicating vegetation decline) or δ NDVI: +0.043 (shown in green, indicating improvement).



Bug 10: Zone breakdown labels run together without spacing    MEDIUM 

What you see
In the Zone Breakdown section, the zone name and change classification are concatenated without any separator or line break: 'maharashtra_marathwadaurban growth (73%)' and 'maharashtra_vidarbhaurban growth (68%)'. The zone name and the change label are running directly into each other.

Root cause
The frontend component is rendering the zone_name and change_class fields from the API response as adjacent inline text elements with no space, line break, or separator between them. Either the component template is missing a space character or line break, or the two values are being concatenated with string concatenation rather than placed in separate HTML elements.

Fix
	•	Separate the zone name and change class into two lines. The zone name should be on the first line, bold, in a readable format. Convert maharashtra_marathwada to 'Marathwada, Maharashtra' — replace underscores with spaces and capitalise properly.
	•	The change class and confidence percentage should be on the second line, smaller text, with the confidence value in a colour-coded badge: green for Stable Vegetation, orange for Cropland Expansion or Urban Growth, red for Deforestation.
	•	Add 8-12px of vertical padding between each zone entry in the breakdown list.

Zone name formatting rule:
Apply this transformation to all zone names before displaying them: replace all underscores with spaces, split on the first underscore to separate state name from zone name, capitalise each word. Examples: maharashtra_marathwada becomes 'Marathwada (Maharashtra)', punjab_central becomes 'Central Punjab', gangetic_plain_west becomes 'Western Gangetic Plain'.

Implementation Order and Time Plan

Fix these bugs in the following order. The order is determined by: severity first, then dependency (some frontend fixes require backend fixes to be done first).

Order
Bug #
Task
Est. Time
Can demo without fix?
1
Bug 4
Fix Satellite Pass Predictor JSON error — diagnose N2YO API key and add error handling
1-2 hrs
NO
2
Bug 3
Fix Verify Predictions — diagnose empty state, check DB, check CORS, check route registration
2-3 hrs
NO
3
Bug 8
Fix NDVI map — render all states with NDVI colours, not just selected state
2-3 hrs
NO
4
Bug 5
Update launch countdown to next real upcoming ISRO mission
1 hr
NO
5
Bug 1+2
Fix model card empty fields + replace PDF button with inline modal
2-3 hrs
Partial
6
Bug 9
Fix Total Δ NDVI empty field
1 hr
YES
7
Bug 7
Add SHAP breakdown card below launch probability gauge
2-3 hrs
YES
8
Bug 6
Fix Starlink showing in ISRO filter
30 min
YES
9
Bug 10
Fix zone label formatting
30 min
YES

Total estimated time: 13 to 18 hours. The first four fixes (Bugs 4, 3, 8, 5) are non-negotiable before any demo or evaluation. The remaining five are important but the platform is demoable without them.

Quick Reference: What Each Page Should Look Like After All Fixes

Research Lab
	•	Verify Predictions tab: shows a table of 10 recent predictions, all with VERIFIED status and visible hash values. Input field works and returns VERIFIED for any valid asteroid designation.
	•	Model Cards tab: all three cards show populated Training Data and Latest Benchmark fields. Clicking the button opens a modal with full card content.
	•	Audit Log tab: shows timestamped verification events.

Astronomy — Satellites
	•	Satellite Pass Predictor: clicking Find Passes returns a table of upcoming ISS passes for Mumbai with date, time, duration, max elevation, and direction. No JSON error.

Astronomy — Launches
	•	Next launch countdown shows a future ISRO mission with a real countdown ticking down.
	•	ISRO filter shows only ISRO missions — no SpaceX or NASA entries.
	•	AI Prediction card shows probability gauge AND a SHAP bar chart AND a solar risk chip.

Earth — Vegetation
	•	NDVI map shows all Indian states filled with colour: green, amber, or red based on their NDVI value. Selected state has a bold border.
	•	Total Δ NDVI shows a signed decimal value in colour (red for decline, green for improvement).
	•	Zone breakdown shows properly formatted zone names and change labels on separate lines with spacing.
