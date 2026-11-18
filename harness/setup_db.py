"""Load identical synthetic data into Oracle and Trino."""
from generate_data import generate
from db import load_oracle, load_trino

if __name__ == "__main__":
    data = generate()
    print("Loading Oracle...")
    load_oracle(data)
    print("Loading Trino...")
    load_trino(data)
    print({t: len(r) for t, r in data.items()})
