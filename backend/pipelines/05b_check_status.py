# 05b_check_status.py
# Monitor GEE task progress from terminal
# Run this anytime to see which zones are done

import ee
import json
import time
import os

EE_PROJECT = os.getenv("EE_PROJECT")
if EE_PROJECT:
    ee.Initialize(project=EE_PROJECT)
else:
    ee.Initialize()

TASK_IDS_FILE = '../data/gee_task_ids.json'
STATUS_EMOJI  = {
    'READY':     '⏳ queued',
    'RUNNING':   '🔄 running',
    'COMPLETED': '✅ done',
    'FAILED':    '❌ failed',
    'CANCELLED': '🚫 cancelled',
    'SUBMITTED': '📤 submitted',
}


def check_all_tasks(watch=False, interval=120):
    """
    Check status of all submitted GEE tasks.
    watch=True: keep polling until all complete.
    interval: seconds between polls when watching.
    """
    if not os.path.exists(TASK_IDS_FILE):
        print('No task IDs file found. Run 05_submit_gee_tasks.py first.')
        return

    while True:
        with open(TASK_IDS_FILE) as f:
            all_tasks = json.load(f)

        counts    = {'COMPLETED': 0, 'RUNNING': 0, 'READY': 0,
                     'FAILED': 0, 'UNKNOWN': 0}
        completed = []
        failed    = []

        print('\n' + '=' * 65)
        print(f'AstroGeo GEE Task Status — {time.strftime("%H:%M:%S")}')
        print('=' * 65)
        print(f'{"Zone":<35} {"Status":<20} {"Task ID":<15}')
        print('-' * 65)

        for zone_name, task_info in all_tasks.items():
            task_id = task_info.get('task_id')

            if not task_id:
                status = 'FAILED_TO_SUBMIT'
                display = '❌ not submitted'
            else:
                try:
                    raw    = ee.data.getTaskStatus(task_id)[0]
                    status = raw['state']
                    progress = raw.get('progress', 0)
                    display  = STATUS_EMOJI.get(status, status)
                    if status == 'RUNNING' and progress:
                        display += f' {progress*100:.0f}%'
                except Exception as e:
                    status  = 'UNKNOWN'
                    display = f'❓ error: {str(e)[:20]}'

            counts[status if status in counts else 'UNKNOWN'] += 1
            short_id = task_id[:12] + '...' if task_id else 'none'
            print(f'{zone_name:<35} {display:<20} {short_id}')

            if status == 'COMPLETED':
                completed.append(zone_name)
            elif status == 'FAILED':
                failed.append(zone_name)

        print('=' * 65)
        total = len(all_tasks)
        print(f'Summary: ✅ {counts["COMPLETED"]}/{total} done  '
              f'🔄 {counts["RUNNING"]} running  '
              f'⏳ {counts["READY"]} queued  '
              f'❌ {counts["FAILED"]} failed')

        if failed:
            print(f'\nFailed zones (re-run 05_submit_gee_tasks.py):')
            for z in failed:
                print(f'  {z}')

        all_done = counts['COMPLETED'] + counts['FAILED'] == total

        if all_done or not watch:
            if all_done:
                if failed:
                    print(f'\n⚠️  {len(failed)} zones failed.')
                    print('Re-run 05_submit_gee_tasks.py to retry failed zones.')
                else:
                    print('\n🎉 All zones completed!')
                    print('Run 05c_download_and_merge.py to get your CSV.')
            break
        else:
            remaining = total - counts['COMPLETED'] - counts['FAILED']
            print(f'\nNext check in {interval}s ({remaining} zones pending)...')
            print('Press Ctrl+C to stop watching.')
            time.sleep(interval)


if __name__ == '__main__':
    import sys
    # python 05b_check_status.py         → check once
    # python 05b_check_status.py watch   → keep watching until done
    watch = len(sys.argv) > 1 and sys.argv[1] == 'watch'
    check_all_tasks(watch=watch, interval=120)
