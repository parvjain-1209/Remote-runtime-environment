"""
CLI script to render an otpauth URI as a terminal QR code using segno.
Usage: python scripts/da3_qr.py <otpauth_uri>
"""

import sys
import segno


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/da3_qr.py <otpauth_uri>", file=sys.stderr)
        sys.exit(1)

    uri = sys.argv[1]
    qr = segno.make(uri)
    qr.terminal(compact=True)


if __name__ == "__main__":
    main()
