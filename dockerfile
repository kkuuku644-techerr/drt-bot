flyctl deploy --build-only --push -a drt-bot --image-label deployment-4f471422090fb9e547e4914990d3de47 --config fly.toml

==> Verifying app config

Validating fly.toml

✓ Configuration is valid

--> Verified app config

==> Building image

==> Building image

Error: failed to fetch an image or build from source: unauthorized (Request ID: 01KZDJKEXY44G89GQXMY5GJVNS-iad) (Trace ID: 090346118de0e90376f6c747cfc334b1)

Dockerfile failed to build error

unsuccessful command 'flyctl deploy --build-only --push -a drt-bot --image-label deployment-4f471422090fb9e547e4914990d3de47 --config fly.toml'
