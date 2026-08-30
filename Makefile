.PHONY: prepare check verify look-scanner look-firstglance look-sleuth look-sleuth-hard compare prove-hallofmirrors test tidy

SOLC_VERSIONS ?= 0.4.24 0.4.25 0.5.16 0.6.12 0.7.6 0.8.20 0.8.23

prepare:
	@command -v forge >/dev/null || (echo "Foundry missing. See REPRODUCTION.md" && exit 1)
	forge install --root proofground foundry-rs/forge-std --no-git || true
	pip install -e ".[dev]"
	@command -v solc-select >/dev/null && solc-select install $(SOLC_VERSIONS) || echo "solc-select missing; needed for the old-solc cases"

check:
	culpa check

look-scanner:
	culpa investigate --who scanner --cases quick --into findings/scanner.json

look-firstglance:
	culpa investigate --who first-glance --cases quick --into findings/firstglance.json

look-sleuth:
	culpa investigate --who sleuth --cases quick --into findings/sleuth.json

look-sleuth-hard:
	culpa investigate --who sleuth --cases hard --into findings/sleuth_hard.json

compare:
	culpa compare findings/scanner.json findings/sleuth.json --into findings/comparison.md

verify:
	culpa verify

prove-hallofmirrors:
	cp casework/proofs/HallOfMirrors.t.sol proofground/test/staged/ProveHallOfMirrors.t.sol
	forge test --root proofground --match-contract ProveHallOfMirrors -vvv --allow-paths "$(PWD)/casework"

test:
	pytest -q

tidy:
	rm -rf proofground/out proofground/cache proofground/test/staged/*.t.sol findings/*.json
