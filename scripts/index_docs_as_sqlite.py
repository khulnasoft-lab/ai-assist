# Indexes gitlab documentation to create embeddable search for self-hosted
# AIGW instances. This was initially added to GitLab-rails repository, but it
# is only used when building the docker image here.

import argparse
import glob
import json
import logging
import os
import re
import sqlite3
import sys
import tempfile
from zipfile import ZipFile

import requests
from langchain.docstore.document import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Function to parse command-line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate GitLab docs index.")

    parser.add_argument("-o", "--output_path", help="Output path", default="docs.db")
    parser.add_argument(
        "-v",
        "--version_tag",
        help="GitLab version tag to include in the URL (e.g., v17.1.0-ee)",
        default="master",
    )
    return parser.parse_args()


def execution_error(error_message):
    logger.error(error_message)
    sys.exit(1)


# Function to fetch documents from GitLab
def fetch_documents(version_tag):
    docs_url = f"https://gitlab.com/gitlab-org/gitlab/-/archive/{version_tag}/gitlab-{version_tag}.zip?path=doc"
    print(docs_url)

    response = requests.get(docs_url, timeout=100)

    if response.status_code != 200:
        return execution_error(
            f"Failed to download documents. Status code: {response.status_code}"
        )

    tmpdirname = tempfile.mkdtemp()
    zip_path = os.path.join(tmpdirname, "docs.zip")
    with open(zip_path, "wb") as f:
        f.write(response.content)
    with ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(tmpdirname)

    # Find the directory that was extracted
    extracted_dirs = [
        os.path.join(tmpdirname, name)
        for name in os.listdir(tmpdirname)
        if os.path.isdir(os.path.join(tmpdirname, name))
    ]
    if not extracted_dirs:
        execution_error("No directory found after extraction. Exiting.")

    logger.info("Documents are fetched.")
    extracted_dir = extracted_dirs[0]
    logger.info("Extracted documents to %s", extracted_dir)
    return extracted_dir


def build_row_corpus(row):
    corpus = row["content"]
    # Remove the preamble
    preamble_start = corpus.find("---")
    if preamble_start != -1:
        preamble_end = corpus.find("---", preamble_start + 1)
        corpus = corpus[preamble_end + 2 : -1]
    if not corpus:
        return ""
    # Attach the titles to the corpus, these can still be useful
    corpus = (
        "".join(row["metadata"].get(f"Header{i}", "") for i in range(1, 6))
        + " "
        + corpus
    )
    # Stemming could be helpful, but it is already applied by the sqlite
    # Remove punctuation and set to lowercase, this should reduce the size of the corpus and allow
    # the query to be a bit more robust
    corpus = corpus.lower()
    corpus = re.sub(r"[^\w\s]", "", corpus)
    return corpus


# Function to process documents and create the database
def create_database(path, output_path):
    files = glob.glob(os.path.join(path, "doc/**/*.md"), recursive=True)
    if not files:
        execution_error("No markdown files found")

    documents = []

    # Read all the files
    for filename in files:
        with open(filename, "r") as f:
            doc = Document(page_content=f.read(), metadata={"filename": filename})
            documents.append(doc)

    # Split content into chunks by its header
    headers_to_split_on = [
        ("#", "Header1"),
        ("##", "Header2"),
        ("###", "Header3"),
        ("####", "Header4"),
        ("#####", "Header5"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on
    )
    rows_to_insert = []

    for d in documents:
        md_header_splits = markdown_splitter.split_text(d.page_content)
        for chunk in md_header_splits:
            metadata = {**chunk.metadata, **d.metadata}
            rows_to_insert.append({"content": chunk.page_content, "metadata": metadata})

    for r in rows_to_insert:
        r["processed"] = build_row_corpus(r)
    # sql_tuples = [(r['processed'], r['content'], r['metadata']['filename']) for r in rows_to_insert if r['processed']]
    sql_tuples = [
        (r["processed"], r["content"], json.dumps(r["metadata"]))
        for r in rows_to_insert
        if r["processed"]
    ]

    if os.path.exists(output_path):
        os.remove(output_path)
        logger.info("Deleted existing file at %s", output_path)

    # Create the database
    conn = sqlite3.connect(output_path)
    c = conn.cursor()
    c.execute(
        "CREATE VIRTUAL TABLE doc_index USING fts5(processed, content, metadata, tokenize='porter trigram');"
    )
    c.execute("PRAGMA user_version = 1;")
    c.executemany(
        "INSERT INTO doc_index (processed, content, metadata) VALUES (?,?,?)",
        sql_tuples,
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    args = parse_arguments()

    docs_path = fetch_documents(version_tag=args.version_tag)

    if not docs_path:
        execution_error("Fetching documents failed")

    output_path = args.output_path
    create_database(docs_path, output_path)
    logger.info("Database created at %s", output_path)
