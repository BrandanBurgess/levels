.PHONY: bootstrap dev lint typecheck test build seed e2e verify clean

bootstrap:
	npm run bootstrap

dev:
	npm run dev

lint:
	npm run lint

typecheck:
	npm run typecheck

test:
	npm run test

build:
	npm run build

seed:
	npm run seed

e2e:
	npm run e2e

verify:
	npm run verify

clean:
	npm --workspace @levels/web run clean
	uv clean
