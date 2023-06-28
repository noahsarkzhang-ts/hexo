---
title: Metricbeat
date: 2022-06-05 12:54:37
updated: 2022-06-05 12:54:37
tags:
- metricbeat
- metric
- kibana
categories:
- Elasticsearch
---

这篇文章包含两部分内容：1）使用 Metricbeat 采集系统 metric 指标; 2）分析 Metricbeat 的存储模型。

<!-- more -->

## 概述

Metricbeat 是一个轻量型指标采集器，用于从系统和服务收集指标。Metricbeat 能够以一种轻量型的方式，输送各种系统和服务统计数据，从 CPU 到内存，从 Redis 到 Nginx，不一而足。其流程如下所示：

![metricbeat-flow](/images/es/metricbeat-flow.jpg "metricbeat-flow")

Metric 数据采集的方式与 ELK 的流程是一致的，差别只是采集工具是 Metricbeat.

在本文中，我们只安装 Metricbeat, Elasticsearch 及 Kibana 安装部署参考之前的文章：[Docker 下安装 ES, Kibana](https://zhangxt.top/2022/01/29/es-deployment-in-docker/)

**约定：**
Metricbeat, Elasticsearch 及 Kibana 三个组件的版本为：V7.14.2.

## 安装 Metricbeat

### 下载及部署 Metricbeat
从官方网址下载指定的版本：[Metricbeat 下载地址](https://www.elastic.co/cn/downloads/past-releases/metricbeat-7-14-2) 

```bash
# 下载 Metricbeat
$ wget https://artifacts.elastic.co/downloads/beats/metricbeat/metricbeat-7.14.2-linux-x86_64.tar.gz

# 解压缩
$ tar -xzvf metricbeat-7.14.2-linux-x86_64.tar.gz
```

### 修改 metricbeat.yaml

```yaml
# ================================= Dashboards =================================
# 从本地导入 dashboard 模板
setup.dashboards.enabled: true 

# =================================== Kibana ===================================
# 导入 dashboards 需要登陆 Kibana
setup.kibana:

  # 设置 kibana 地址及用户名/密码
  host: "192.168.1.100:5601"
  protocol: "http"
  username: "elastic"
  password: "yourpassword"

# ---------------------------- Elasticsearch Output ----------------------------
output.elasticsearch:
  # 配置 Elasticsearch 地址
  hosts: ["192.168.1.100:9200"]

  # 设置协议 Protocol - either `http` (default) or `https`.
  protocol: "http"
  
  # 设置 username/password
  username: "elastic"
  password: "yourpassword"
```

从本地导入 dashboard, 在 kibana 上可方便查看 metric 信息。

### 开启模块

Metricbeat 自带了很多监控模块，如 Mysql, 默认开启 `system` 模块，可以根据需要添加模块：

```bash
# 查看 metircbeat 开启的模块
$ ./metricbeat modules list
Enabled:
system

Disabled:
activemq
aerospike
apache
appsearch
aws
awsfargate
azure
beat
beat-xpack
ceph
ceph-mgr
cloudfoundry
...

# 开启模块
$ ./metricbeat modules enable 模块名

# 关闭模块
$ ./metricbeat modules disenable 模块名

```

可以通过文件 `./modules.d/system.yml` 查看监控的详细信息等。

### 启动 Metricbeat

```bash
nohup ./metricbeat -e -c metricbeat.yml > metricbeat.log 2>&1 &
```

### System Metric 数据

Metric 上报的数据格式如下所示：

```json
{
    "monitoring":{
        "metrics":{
            "beat":{
                "cgroup":{
                    "cpu":{
                        "cfs":{
                            "period":{
                                "us":100000
                            }
                        },
                        "id":"user.slice"
                    },
                    "cpuacct":{
                        "id":"user.slice",
                        "total":{
                            "ns":229167185975607
                        }
                    },
                    "memory":{
                        "id":"user.slice",
                        "mem":{
                            "limit":{
                                "bytes":9223372036854771712
                            },
                            "usage":{
                                "bytes":2822836224
                            }
                        }
                    }
                },
                "cpu":{
                    "system":{
                        "ticks":10380270,
                        "time":{
                            "ms":10380278
                        }
                    },
                    "total":{
                        "ticks":20076350,
                        "time":{
                            "ms":20076360
                        },
                        "value":20076350
                    },
                    "user":{
                        "ticks":9696080,
                        "time":{
                            "ms":9696082
                        }
                    }
                },
                "handles":{
                    "limit":{
                        "hard":4096,
                        "soft":1024
                    },
                    "open":10
                },
                "info":{
                    "ephemeral_id":"65c6d0a4-cf03-4e09-9011-fd649b3afa80",
                    "uptime":{
                        "ms":359285941
                    },
                    "version":"7.14.2"
                },
                "memstats":{
                    "gc_next":18072816,
                    "memory_alloc":10275848,
                    "memory_sys":77612040,
                    "memory_total":646879155368,
                    "rss":129318912
                },
                "runtime":{
                    "goroutines":23
                }
            },
            "libbeat":{
                "config":{
                    "module":{
                        "running":3,
                        "starts":3
                    },
                    "reloads":1,
                    "scans":1
                },
                "output":{
                    "events":{
                        "acked":806376,
                        "active":21,
                        "batches":35917,
                        "total":806397
                    },
                    "read":{
                        "bytes":18887264,
                        "errors":1
                    },
                    "type":"elasticsearch",
                    "write":{
                        "bytes":2675036055
                    }
                },
                "pipeline":{
                    "clients":0,
                    "events":{
                        "active":0,
                        "published":806376,
                        "retry":70,
                        "total":806376
                    },
                    "queue":{
                        "acked":806376,
                        "max_events":4096
                    }
                }
            },
            "metricbeat":{
                "system":{
                    "cpu":{
                        "events":35919,
                        "success":35919
                    },
                    "filesystem":{
                        "events":17961,
                        "success":17961
                    },
                    "fsstat":{
                        "events":5987,
                        "success":5987
                    },
                    "load":{
                        "events":35919,
                        "success":35919
                    },
                    "memory":{
                        "events":35919,
                        "success":35919
                    },
                    "network":{
                        "events":323270,
                        "success":323270
                    },
                    "process":{
                        "events":279163,
                        "success":279163
                    },
                    "process_summary":{
                        "events":35919,
                        "success":35919
                    },
                    "socket_summary":{
                        "events":35919,
                        "success":35919
                    },
                    "uptime":{
                        "events":400,
                        "success":400
                    }
                }
            },
            "system":{
                "cpu":{
                    "cores":4
                },
                "load":{
                    "1":0.03,
                    "15":0.05,
                    "5":0.05,
                    "norm":{
                        "1":0.0075,
                        "15":0.0125,
                        "5":0.0125
                    }
                }
            }
        }
    }
}
```

## 查看 Metric 监控

可以在 `kibana` dashboard 查看监控数据。

![kibana-metric-dashboard](/images/es/kibana-metric-dashboard.jpg "kibana-metric-dashboard")

可以在三种视图间切换：System Overview, Host Overview, Containers overview.
![kibana-metric-dashboard](/images/es/kibana-metric-dashboard-system.jpg "kibana-metric-dashboard")

## 数据模型

Metricbeat 所有的 Metric 数据存储在一张表中，预置了 3949 个字段，而大部分的字段是空的，没有值。

### Index Mapping

在 Mapping 中，按照模块组织字段，如 activemq, apache, system 等等。

```json
{
    "mappings":{
        "_doc":{
            "_meta":{
                "beat":"metricbeat",
                "version":"7.14.2"
            },
            "dynamic_templates":Array[88],
            "date_detection":false,
            "properties":{
                "@timestamp":{
                    "type":"date"
                },
                "activemq":Object{...},
                "aerospike":Object{...},
                "agent":Object{...},
                "apache":Object{...},
                ...
                "system":{
                    "properties":{
                        "core":Object{...},
                        "cpu":Object{...},
                        "diskio":Object{...},
                        "entropy":Object{...},
                        "filesystem":Object{...},
                        "fsstat":Object{...},
                        "load":Object{...},
                        "memory":Object{...},
                        "network":Object{...},
                        "network_summary":Object{...},
                        "process":Object{...},
                        "raid":Object{...},
                        "service":Object{...},
                        "socket":Object{...},
                        "uptime":Object{...},
                        "users":Object{...}
                    }
                },
				...
			}
		}
	}
}
```

### 稀疏数据

在 Elasticsearch 6.0 (Lucene 7.0 ) 之前的版本中，Doc values 适合存储紧凑性的数据，这些数据所有字段都有值，对于稀疏数据（有很多空值），需要额外的空间来维护这些空值，会造成存储空间的浪费，也会影响索引的速度。什么类型的数据是稀疏数据呢？如下图所示：

![sparse-data](/images/es/sparse-data.jpg "sparse-data")

如果文档中的字段只有很少一部分有值，那这个字段可以称为稀疏数据，如 `middle`, `city` , `state`.

在 Lucene 7.0 (Elasticsearch 6.0 配套的 Lucene 版本) 内部使用迭代器方式遍历数据，它可以更有效的使用存储空间。

![docvalus-iteerator](/images/es/docvalus-iteerator.jpg "docvalus-iteerator")

如上图所示，使用随机访问方式遍历 doc values(Elasticsearch 6.0 之前版本使用的方式), 需要维护空值。而迭代器方式则不需要存储空值，可以有效地节省存储空间。

除了存储空间的优化，迭代器方式也可以提升索引的速度，虽然有了这些优化，还是尽量避免使用稀疏数据，相比较而言，紧凑性数据更为有效。


</br>

**参考：**

----
[1]:https://www.elastic.co/guide/en/beats/metricbeat/current/setup-kibana-endpoint.html
[2]:https://blog.csdn.net/weixin_34409741/article/details/88664175
[3]:https://www.elastic.co/cn/blog/minimize-index-storage-size-elasticsearch-6-0

[1. Configure the Kibana endpoint][1]
[2. ELK MetricBeat配置监控主机性能][2]
[3. Elasticsearch 6.0: Sparse Field Improvements][3]