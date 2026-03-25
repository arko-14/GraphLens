from app.db.schema_setup import create_indexes
import logging

if __name__ == "__main__":
    logging.info("Rebuilding indexes...")
    create_indexes()
    logging.info("Done.")
