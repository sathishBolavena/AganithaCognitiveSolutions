import argparse
import logging
from typing import Optional
from .core import PubMedFetcher
import pandas as pd

def setup_logging(debug: bool = False) -> None:
    """Configure logging level."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=level
    )

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch PubMed papers with industry affiliations"
    )
    parser.add_argument(
        "query",
        type=str,
        help="PubMed search query"
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="Output CSV filename"
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--email",
        type=str,
        default="your_email@example.com",
        help="Email for PubMed API (required)"
    )
    return parser.parse_args()

def main():
    """Main entry point."""
    args = parse_args()
    setup_logging(args.debug)
    
    fetcher = PubMedFetcher(email=args.email)
    papers = fetcher.fetch_papers(args.query)
    
    if not papers:
        logging.warning("No papers with industry affiliations found")
        return
    
    df = pd.DataFrame(papers)
    
    if args.file:
        df.to_csv(args.file, index=False)
        logging.info(f"Results saved to {args.file}")
    else:
        print(df.to_string(index=False))

if __name__ == "__main__":
    main()