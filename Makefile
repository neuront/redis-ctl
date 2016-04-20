# redis cluster nodes

define REDIS_CLUSTER_NODE_CONF_A
daemonize yes
port 7100
cluster-node-timeout 5000
pidfile /tmp/redis_cluster_node_a.pid
logfile /tmp/redis_cluster_node_a.log
save ""
appendonly no
cluster-enabled yes
cluster-config-file /tmp/redis_cluster_node_a.conf
endef

define REDIS_CLUSTER_NODE_CONF_B
daemonize yes
port 7101
cluster-node-timeout 5000
pidfile /tmp/redis_cluster_node_b.pid
logfile /tmp/redis_cluster_node_b.log
save ""
appendonly no
cluster-enabled yes
cluster-config-file /tmp/redis_cluster_node_b.conf
endef

define REDIS_CLUSTER_NODE_CONF_C
daemonize yes
port 7102
cluster-node-timeout 5000
pidfile /tmp/redis_cluster_node_c.pid
logfile /tmp/redis_cluster_node_c.log
save ""
appendonly no
cluster-enabled yes
cluster-config-file /tmp/redis_cluster_node_c.conf
endef

ifndef REDIS_SERVER
	REDIS_SERVER=redis-server
endif

export REDIS_CLUSTER_NODE_CONF_A
export REDIS_CLUSTER_NODE_CONF_B
export REDIS_CLUSTER_NODE_CONF_C

help:
	@echo "Use 'make <target>', where <target> is one of"
	@echo "  clean     remove temporary files"
	@echo "  test      run test suite"

clean:
	-find . -type f -name "*.pyc" -exec rm -f "{}" \;

start-test:clean-test
	@echo "Wait several seconds for Redis cluster ready"
	@sleep 1
	@echo "$$REDIS_CLUSTER_NODE_CONF_A" | $(REDIS_SERVER) -
	@echo "$$REDIS_CLUSTER_NODE_CONF_B" | $(REDIS_SERVER) -
	@echo "$$REDIS_CLUSTER_NODE_CONF_C" | $(REDIS_SERVER) -
	@sleep 5

clean-test:stop-test
	@rm -f /tmp/redis_cluster_node*.conf
	@rm -f dump.rdb appendonly.aof

stop-test:
	@test -e /tmp/redis_cluster_node_a.pid && kill `cat /tmp/redis_cluster_node_a.pid` || true
	@test -e /tmp/redis_cluster_node_b.pid && kill `cat /tmp/redis_cluster_node_b.pid` || true
	@test -e /tmp/redis_cluster_node_c.pid && kill `cat /tmp/redis_cluster_node_c.pid` || true
	@rm -f /tmp/redis_cluster_node_*.conf

test:start-test
	@python -m unittest discover -s test/ -p "*.py"
	@make stop-test
	@echo "================="
	@echo "| Test done \o/ |"
