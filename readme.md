# Canada Job Bank Scraper

Quick little script written in Python to scrape the Canada Job Bank for job postings.

Run the python script with `py jobs_scraper.py`, you will be prompted for input.

### inputs
- keyword
- max results


### outputs
- job_postings.csv


### notes
- requests are sometimes blocked by the server and max results records will not be recorded
- open index.html and drag job_postings.csv into the file upload to view the data in a table
- rates are normalized to annual compensation
- date is yyyy-MM-dd


job_postings.csv