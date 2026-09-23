import argparse

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="XPesquisa — pesquisa científica local")
    parser.add_argument("command", choices=["serve"])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    uvicorn.run("xpesquisa.api:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
