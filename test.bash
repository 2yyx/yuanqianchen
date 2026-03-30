curl --location --request POST 'https://facade-api.byted.org/api/v2/hosts/search' \
--header 'X-Jwt-Token: jwt' \
--header 'Content-Type: application/json'
--data '{
  "package__prefix": "均衡",
  "mix": true,
  "node_ids": 85181
  "mem_size__gt": 1024,
  "has_ssd": true
}'

curl --location --request POST 'https://facade-api.byted.org/facade/api/v1/host/r/mGetHosts' \
--header 'X-Jwt-Token: jwt' \
--header 'Content-Type: application/json' \
--data '{
  "modules": ["ecs"],
  "ips": ["2605:340:cd51:6300:d0a1:5def:bd93:aeed"]
}'