# Aleph.im Nodes List

Pre-fetch info from each resource node for the diverse ALEPH frontends.

Use a cache to not hammer the nodes too much. Implemented as an aleph program

The service exposes a Swagger UI at `/docs` and a Redoc UI at `/redoc`.
Use it to explore the available endpoints.



## Development

```shell
pip install hatch
cd src
hatch run uvicorn nodes_list:app --reload
````

### Testing

Test the code quality using `mypy`, `black`, `isort` and `ruff`:
```shell
hatch run linting:all
```

Reformat the code using `black`, `isort` and `ruff`:
```shell
hatch run linting -f
```

Run the tests:
```shell
hatch run testing:test .
```

Export the coverage in HTML:
```shell
hatch run testing:coverage html```


## Deployment

```shell
hatch run deployment:aleph program upload src nodes_list:app
```

Update an existing deployment:

```shell
hatch run deployment:aleph program update $ITEM_HASH src
```