# Task Schema

Use this schema for `scripts/xhs_full_note_collect.py`.

## Minimal Profile Task

```json
{
  "task_name": "xhs_designers_daily",
  "max_notes_per_blogger": 1,
  "skip_existing": true,
  "only_image_text": true,
  "download_images": true,
  "scroll_pages": 3,
  "targets": [
    {
      "name": "上海设计师",
      "url": "https://www.xiaohongshu.com/user/profile/..."
    }
  ]
}
```

## Direct Note Task

```json
{
  "task_name": "single_note_archive",
  "download_images": true,
  "note_urls": [
    {
      "name": "厚来设计",
      "url": "https://www.xiaohongshu.com/explore/NOTE_ID_HERE"
    }
  ]
}
```

## Fields

- `task_name`: Optional name used in summary files.
- `targets`: Blogger profile objects with `name` and `url`.
- `note_urls`: Direct note objects with `name` and `url`.
- `max_notes_per_blogger`: Number of new image-text notes to archive per profile. Default `1`.
- `skip_existing`: Skip note IDs already present in existing `metadata.json` files. Default `true`.
- `only_image_text`: Reject video notes. Default `true`.
- `download_images`: Download images into `images/`. Default `true`.
- `scroll_pages`: Number of profile-page scrolls to load more candidates. Default `3`.
- `target_sleep_seconds`: Delay between profiles. Default `2`.
- `candidate_sleep_seconds`: Delay after opening a note. Default `3`.

## Output Contract

Each successful note directory contains:

- `body.txt`: title, blogger, source URL, metrics, and body copy.
- `metadata.json`: machine-readable note metadata, counts, local image files, and source URLs.
- `image_urls.txt`: ordered image URLs.
- `full_text_snapshot.txt`: visible note detail text for debugging.
- `采集状态.txt`: human-readable status.
- `images/`: downloaded image files.

The runner also writes:

- `<task_name>_summary.json`
- `<task_name>_summary.csv`
- `<task_name>_summary.md`
