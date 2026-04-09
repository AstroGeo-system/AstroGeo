# 05_submit_gee_tasks.py
# AstroGeo — Submit GEE export tasks for all 17 India zones
# Run AFTER confirming GEE works (Steps 1–4 passed)
# Each task exports a CSV of sampled pixels to Google Drive

import ee
import json
import os
import time
from geospatial_agent import (
    build_training_image_for_zone,
    generate_pipeline_hash,
    INDIA_ZONES,
    ANALYSIS_YEARS,
)

EE_PROJECT = os.getenv("EE_PROJECT")
if EE_PROJECT:
    ee.Initialize(project=EE_PROJECT)
else:
    ee.Initialize()

DRIVE_FOLDER    = 'AstroGeo_GEE_Exports'
SAMPLES_PER_CLASS = 300      # 300 × 4 classes × 17 zones = ~20,400 rows total
SAMPLE_SCALE    = 100        # 100m resolution — safe for India-scale
TASK_IDS_FILE   = '../data/gee_task_ids.json'


def submit_zone_task(zone_name: str) -> dict:
    """
    Build training image for one zone and submit export task to GEE.
    Returns task info dict.
    """
    config = INDIA_ZONES[zone_name]
    print(f'\n[{zone_name}]')
    print(f'  States: {", ".join(config["states"])}')
    print(f'  Window: month {config["start_month"]} → {config["end_month"]}',
          '(next yr)' if config['year_offset'] else '')
    print(f'  Cloud threshold: {config["cloud_threshold"]}%')

    # Build the 8-band training image on GEE servers
    print(f'  Building training image...')
    training_image, aoi = build_training_image_for_zone(zone_name)

    # Stratified sample — forces balanced classes regardless of pixel counts
    print(f'  Setting up stratified sample ({SAMPLES_PER_CLASS}/class × 4 classes)...')
    samples = training_image.stratifiedSample(
        numPoints=SAMPLES_PER_CLASS,
        classBand='change_class',
        region=aoi,
        scale=SAMPLE_SCALE,
        seed=42,                  # reproducible
        geometries=False,         # no coordinates — smaller CSV
        tileScale=4,              # prevents OOM on large regions
    )

    # Submit export task to Google Drive (v2 exports with improved labels)
    task = ee.batch.Export.table.toDrive(
        collection=samples,
        description=f'ndvi_v2_{zone_name}',
        folder=DRIVE_FOLDER,
        fileNamePrefix=f'ndvi_v2_{zone_name}',
        fileFormat='CSV',
    )
    task.start()

    pipeline_hash = generate_pipeline_hash(zone_name, ANALYSIS_YEARS)

    task_info = {
        'zone':             zone_name,
        'task_id':          task.id,
        'states':           config['states'],
        'pipeline_hash':    pipeline_hash,
        'submitted_at':     time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'samples_per_class':SAMPLES_PER_CLASS,
        'scale_metres':     SAMPLE_SCALE,
        'drive_folder':     DRIVE_FOLDER,
        'file_name':        f'ndvi_v2_{zone_name}.csv',
        'status':           'SUBMITTED',
    }

    print(f'  Task submitted: {task.id}')
    return task_info


def submit_all_zones() -> dict:
    """Submit export tasks for all 17 zones sequentially."""
    print('=' * 60)
    print('AstroGeo — Submitting GEE export tasks for all India zones')
    print(f'Zones to process: {len(INDIA_ZONES)}')
    print(f'Samples per class per zone: {SAMPLES_PER_CLASS}')
    print(f'Total expected rows: ~{SAMPLES_PER_CLASS * 4 * len(INDIA_ZONES):,}')
    print('=' * 60)

    all_tasks = {}
    failed    = []

    for i, zone_name in enumerate(INDIA_ZONES.keys(), 1):
        print(f'\n--- Zone {i}/{len(INDIA_ZONES)} ---')
        try:
            task_info = submit_zone_task(zone_name)
            all_tasks[zone_name] = task_info

            # Small delay between submissions to avoid rate limiting
            if i < len(INDIA_ZONES):
                time.sleep(2)

        except Exception as e:
            print(f'  ERROR submitting {zone_name}: {e}')
            failed.append(zone_name)
            all_tasks[zone_name] = {
                'zone': zone_name,
                'task_id': None,
                'status': 'FAILED_TO_SUBMIT',
                'error': str(e),
            }

    # Save all task IDs to file
    with open(TASK_IDS_FILE, 'w') as f:
        json.dump(all_tasks, f, indent=2)

    print('\n' + '=' * 60)
    print('SUBMISSION COMPLETE')
    print(f'Successfully submitted: {len(INDIA_ZONES) - len(failed)}/{len(INDIA_ZONES)} zones')
    if failed:
        print(f'Failed zones: {failed}')
        print('Re-run script — it will skip already-submitted zones')
    print(f'\nTask IDs saved to: {TASK_IDS_FILE}')
    print(f'Monitor progress: https://code.earthengine.google.com/tasks')
    print('Expected completion: 2–8 hours (runs on GEE servers)')
    print('Run 05b_check_status.py to monitor without opening browser')
    print('=' * 60)

    return all_tasks


if __name__ == '__main__':
    # Skip zones that already have a task ID saved
    existing = {}
    if os.path.exists(TASK_IDS_FILE):
        with open(TASK_IDS_FILE) as f:
            existing = json.load(f)
        already_done = [z for z, t in existing.items()
                        if t.get('task_id') is not None]
        if already_done:
            print(f'Skipping {len(already_done)} already-submitted zones:')
            for z in already_done:
                print(f'  {z}: {existing[z]["task_id"]}')
            # Remove already-submitted zones from INDIA_ZONES temporarily
            from geospatial_agent import INDIA_ZONES as ALL_ZONES
            remaining = {k: v for k, v in ALL_ZONES.items()
                         if k not in already_done}
            if not remaining:
                print('All zones already submitted. Run 05b_check_status.py')
                exit(0)

    submit_all_zones()
