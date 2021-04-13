# Certificates

The certificates in this directory are self-signed and used for testing Open Zaak
certificate validation. **Do NOT use these in any real deployments.**

Open Zaak has a mode where you can specify additional (root) certificates to trust,
in addition to the [`certifi.where()`][certifi] certificate bundle. These certificates
are used to (automatically) test this.

## Testing

In the root of the repository, run:

```bash
docker-compose -f docker-compose.travis.yml up mock-endpoints.local
```

Now, navigate your browser (or any other HTTP client) to `https://localhost:9001` and
verify that the self-signed certificates are used.

## Generate certificates

The certificates are generated following an [Azure guide][certicate guide].

```bash
# root certificate
openssl ecparam -out openzaak.key -name prime256v1 -genkey
openssl req -new -sha256 -key openzaak.key -out openzaak.csr
openssl x509 -req -sha256 -days 1095 -in openzaak.csr -signkey openzaak.key -out openzaak.crt

# server certificate
openssl ecparam -out mocks.key -name prime256v1 -genkey
openssl req \
    -new \
    -sha256 \
    -key mocks.key \
    -out mocks.csr \
    -config <(cat /etc/ssl/openssl.cnf <(printf "[SAN]\nsubjectAltName=DNS:localhost")) \
    -reqexts SAN

# sign the certificate with the root CA
openssl x509 \
    -req \
    -in mocks.csr \
    -CA openzaak.crt \
    -CAkey openzaak.key \
    -CAcreateserial \
    -out mocks.crt \
    -days 1095 \
    -sha256 \
    -extfile <(cat /etc/ssl/openssl.cnf <(printf "[SAN]\nsubjectAltName=DNS:localhost")) \
    -extensions SAN
```

Note that the certificate expires after about 3 years.

[certifi]: https://pypi.org/project/certifi/
[certificate guide]: https://docs.microsoft.com/en-us/azure/application-gateway/self-signed-certificates
