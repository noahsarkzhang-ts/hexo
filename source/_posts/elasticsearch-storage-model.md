---
title: Elasticsearch 存储模型
date: 2022-02-06 12:20:56
updated: 2022-02-06 12:20:56
tags:
- Docvalues
- 列存
- 行存
categories:
- Elasticsearch
---

Elasticsearch 提供了行存及列存的能力，行存用于搜索功能，列存用于聚合和计算。这两种存储模型在文件系统中是如何实现的？它们之间有什么差异？这篇文章对其做一个简单的分析。

<!-- more -->

## 数据模型

### 基本概念
Elasticsearch 作为一个分布式的搜索引擎，底层存储是基于 Lucene 实现的，它们之间的逻辑关系如下图所示：

![es-lucene](/images/es/es-lucene.jpg "es-lucene")

顶层的 Elasticsearch Index 是一个分布式索引，可以对数据进行分片 (Elasticsearch Shard), 每一个 Shard 对应一个 Lucene Index, 而一个 Lucene Index 由一个或多个 sub index (Segment) 组成。简单理解可可以认为 Elasticsearch 扩展了 Lucene Index 的能力，使其具备了索引分片、索引备份等等分布式的功能。

Elasticsearch index 存储的数据称为 Doc, Doc 本质一个 Json 数据。Doc 进入 Elasticsearch 之后，经过如下的流程，最后会落盘到 Lucene Index 中。

![es-lucene](/images/es/es-lucene-v2.png "es-lucene")

- Index（索引）
类似数据库的表的概念，与传统表不一样的在于，Lucene Index 不用提前创建或定义表的 Scheme. 

- Document（文档）
类似数据库内的行或者文档数据库内的文档的概念，一个Index内会包含多个Document。写入Index的Document会被分配一个唯一的ID，即Sequence Number（更多被叫做DocId）。

- Field（字段）
一个 Document 会由一个或多个 Field 组成，Field 是 Lucene 中数据索引的最小定义单位。Lucene 提供多种不同类型的 Field，例如 StringField、TextField、LongFiled 或 NumericDocValuesField 等，Lucene根据 Field 的类型（FieldType）来判断该数据要采用哪种类型的索引方式（Invert Index、Store Field、DocValues 或 N-dimensional 等）。

- Term 和 Term Dictionary
Lucene 中索引和搜索的最小单位，一个 Field 会由一个或多个 Term 组成，Term 是由 Field 经过 Analyzer（分词）产生。Term Dictionary 即Term词 典，是根据条件查找 Term 的基本索引、

- Segment
一个 Index 由一个或多个 sub-index 构成，sub-index 被称为 Segment。Lucene 的 Segment 设计思想与 LSM 类似，Lucene 中的数据先写入到内存的 buffer 中，达到一定量之后再 flush 成一个 Segment, 在 flush 之前的数据是不可读的，这也是 Lucene 称为提供近实时而非实时查询的原因。Index 只提供 Apend 操作，不提供更操作，但可以被删除，删除是通过记录删除的 DocId 来实现的。所以 ndex 的查询需要对多个 Segment 进行查询并对结果进行合并，还需要处理被删除的文档，为了对查询进行优化，Lucene 会有策略对多个 Segment 进行合并，这点与 LSM 对 SSTable 的 Merge 类似。

- Sequence Number
Sequence Number（后面统一叫 DocId）是 Lucene 中一个很重要的概念，这是一个 Int32 的数值，在 Lucene Index 中，通过 DocId 来唯一标识一个 Doc，这有如下特点。
    1. DocId 在 Segment 内唯一，在 Index 内不惟一，不过借助 Segment之间是有顺序的这个特性，通过一次转换来保证其在 Index 内也是唯一，如一个 Index 内有两个 Segment，每个 Segment 内分别有 100 个 Doc，在Segment 内 DocId 都是 0-100，转换到 Index 级的 DocId，需要将第二个 Segment 的 DocId 范围转换为 100-200。
    2. DocId 在 Segment 内唯一，取值从 0 开始递增。但不代表 DocId 取值一定是连续的，如果有 Doc 被删除，那可能会存在空洞；
    3. 一个文档对应的DocId可能会发生变化，主要是发生在Segment合并时。
Lucene 内最核心的倒排索引，本质上就是 Term 到所有包含该 Term 的文档的 DocId 列表的映射。所以 Lucene 内部在搜索的时候会是一个两阶段的查询，第一阶段是通过给定的 Term 的条件找到所有 Doc 的 DocId 列表，第二阶段是根据 DocId 查找 Doc。Lucene 提供基于 Term 的搜索功能，也提供基于 DocId 的查询功能。

### 索引类型

Lucene 中支持丰富的字段类型，每种字段类型确定了支持的数据类型以及索引方式，目前支持的字段类型包括 LongPoint、TextField、StringField、NumericDocValuesField 等。

![lucene-field](/images/es/lucene-field.png "lucene-field")

Field 有三个重要的属性：
- name(String): 字段的名称，它是一个字符串；
- fieldsData(BytesRef): 字段值，它是一个字节数组；
- type(FieldType): 字段类型，确定了该字段被索引的方式。

FieldType 是一个很重要的类，它包含如下属性：
- stored: 代表是否需要保存该字段，如果为 false，则 lucene 不会保存这个字段的值，而搜索结果中返回的文档只会包含保存了的字段，该字段的内容使用行存格式; 
- tokenized: 代表是否做分词，在 lucene中只有TextField这一个字段需要做分词；
- termVector: 简单来说，term vector 保存了一个文档内所有的 term 的相关信息，包括 Term 值、出现次数（frequencies）以及位置（positions）等，是一个 per-document inverted index，提供了根据
Docid 来查找该文档内所有 term 信息的能力。对于长度较小的字段不建议开启 term verctor，因为只需要重新做一遍分词即可拿到 term 信息，而针对长度较长或者分词代价较大的字段，则建议开启 term vector。Term vector 的用途主要有两个，一是关键词高亮，二是做文档间的相似度匹配（more-like-this）;
- omitNorms: Norms 是 normalization 的缩写，Lucene 允许每个文档的每个字段都存储一个 normalization factor，是和搜索时的相关性计算有关的一个系数。Norms 的存储只占一个字节，但是每个文档的每个字段都会独立存储一份，且 Norms 数据会全部加载到内存。所以若开启了 Norms，会消耗额外的存储空间和内存。但若关闭了 Norms，则无法做 index-time boosting（Elasticsearch 官方建议使用 query-time boosting 来替代）以及 length normalization; 
- indexOptions: Lucene 提供倒排索引的 5 种可选参数（NONE、DOCS、DOCS_AND_FREQS、DOCS_AND_FREQS_AND_POSITIONS、DOCS_AND_FREQS_AND_POSITIONS_AND_OFFSETS），用于选择该字段是否需要被索引，以及索引哪些内容；
- docValuesType: DocValue 是 Lucene 4.0 引入的一个正向索引（Docid 到 field 的一个列存），大大优化了sorting、faceting 或 aggregation 的效率。DocValues 是一个强 schema 的存储结构，开启DocValues 的字段必须拥有严格一致的类型，目前 Lucene 只提供 NUMERIC、BINARY、SORTED、SORTED_NUMERIC 和 SORTED_SET 五种类型；
- dimension：Lucen e支持多维数据的索引，采取特殊的索引来优化对多维数据的查询，这类数据最典型的应用场景是地理位置索引，一般经纬度数据会采取这个索引方式。

### Elasticsearch 数据类型
Elasticsearch 内对用户输入文档进行索引，也是按照 Lucene 能提供的几种模式来提供。除了用户能自定义的 Field，Elasticsearch 还有自己预留的系统字段，用作一些特殊的目的。这些字段映射到 Lucene 本质上也是一个Field，与用户自定义的 Field 无任何区别，只不过 Elasticsearch 根据这些系统字段不同的使用目的，定制有不同的索引方式。

![es-fields](/images/es/es-fields.jpg "es-fields")

- _id
Doc 的主键，在写入的时候，可以指定该 Doc 的 ID 值，如果不指定，则系统自动生成一个唯一的 UUID 值。Lucene 中没有主键索引，要保证系统中同一个 Doc 不会重复，Elasticsearch 引入了 _id 字段来实现主键。每次写入的时候都会先查询 id，如果有，则说明已经有相同Doc存在了。通过 _id 值（ES 内部转换成_uid）可以唯一在 Elasticsearch 中确定一个 Doc。Elasticsearch 中，_id 只是一个用户级别的虚拟字段，在Elasticsearch 中并不会映射到 Lucene 中，所以也就不会存储该字段的值。_id 的值可以由 _uid 解析而来（_uid =type + '#' + id），Elasticsearch 中会存储 _uid; 

- _uid
_uid的格式是：type + '#' + id; 

- _version
Elasticsearch 中每个 Doc 都会有一个 Version，该 Version 可以由用户指定，也可以由系统自动生成。如果是系统自动生成，那么每次 Version 都是递增 1；

- _source
source 是 Elasticsearch 中一个重要的概念，它用来存储原始文档，也可以通过过滤设置只存储特定 Field；

- _seq_no
严格递增的顺序号，每个文档一个，Shard 级别严格递增，保证后写入的 Doc 的 _seq_no 大于先写入的 Doc 的 _seq_no。任何类型的写操作，包括 index、create、update 和 delete，都会生成一个 _seq_no; 

- _primary_term
_primary_term 和 _seq_no 一样是一个整数，每当 Primary Shard 发生重新分配时，比如重启，Primary 选举等，_primary_term 会递增1。_primary_term 主要是用来恢复数据时处理当多个文档的 _seq_no 一样时的冲突，避免 Primary Shard 上的写入被覆盖；

- _routing
路由规则，写入和查询的 routing 需要一致，否则会出现写入的文档没法被查到情况，在 mapping 中，或者 Request 中可以指定按某个字段路由。默认是按照 _Id 值路由；

- _field_names
该字段会索引某个 Field 的名称，用来判断某个 Doc 中是否存在某个 Field，用于 exists 或者 missing 请求。

## 目录结构
在 Elasticsearch 索引数据目录中， 存放了两类关键的数据：1）index, 分片的索引数据；2）translog, Elasticsearch 事务日志，用于数据的恢复。

```bash
# tree -d 1xCBmO0JSoSfyK0sywtQUg/
1xCBmO0JSoSfyK0sywtQUg/
|-- 0
|   |-- index
|   |-- _state
|   `-- translog
`-- _state
```

### 索引目录

index 目录下存放的便是 Lucene 索引文件，由4 segment 组成，segments_xxx文件记录了 Lucene 下面的 Segment 数量。每个segment会包含如下的文件。

```bash
# tree index/
index/
|-- _1aji_1.fnm
|-- _1aji_1_Lucene80_0.dvd
|-- _1aji_1_Lucene80_0.dvm
|-- _1aji.fdm
|-- _1aji.fdt
|-- _1aji.fdx
|-- _1aji.fnm
|-- _1aji.kdd
|-- _1aji.kdi
|-- _1aji.kdm
|-- _1aji_Lucene80_0.dvd
|-- _1aji_Lucene80_0.dvm
|-- _1aji_Lucene84_0.doc
|-- _1aji_Lucene84_0.pos
|-- _1aji_Lucene84_0.tim
|-- _1aji_Lucene84_0.tip
|-- _1aji_Lucene84_0.tmd
|-- _1aji.nvd
|-- _1aji.nvm
|-- _1aji.si
|-- segments_4
...
`-- write.lock
```

文件说明：

| 名称 | 扩展名 | 描述 |
| ---- | ---- | ---- |
| Segment Info | .si | Segment 的元数据文件 |
| Field | .fnm  | 保存了 Fields 的相关信息 |
| Field Index | .fdx | 正排存储文件的元数据信息 |
| Field Data | .fdt | 存储了正排存储数据，写入的原文存储在这 |
| Term Dictionary | .tim | 倒排索引的元数据信息，存储着每个域中 Term 的统计信息且保存着指向 </br> .doc, .pos,  和 .pay 索引文件的指针 |
| Term Index | .tip | 倒排索引文件，保存着 Term 字典的索引信息，可支持随机访问 |
| Frequencies | .doc | 保存了每个 Term 的 Doc Id列表 和 Term 在 Doc 中的词频 |
| Positions | .pos | 保存了 Term 在 Doc 中的位置 |
| Payloads | .pay | 保存了 Term 在 Doc 中的一些高级特性，如 Payloads |
| Norms | .nvd </br> .nvm | 保存 Term 的加权数据 |
| Per-Document Values | .dvd | DocValues 文件，即数据的列式存储，用作聚合和排序 |
| Per-Document Values | .dvm | 存储 DocValues 元数据 |
| Term Vector Data | .tvx </br> .tvd  </br> .tvf | 保存 Term 的矢量信息，用于对 Term 进行高亮、计算文本相关性 |
| Live Documents | .liv | 保存已经删除的 DocId |

## 行存储
对于属性为 stored 的 Field 来说，会写入两种类型的文件：1）.fdt 文件，数据文件；2）.fdx 文件(field index )，是对 .fdt 的一个索引文件。通过索引文件可以方便通过 DocId 找到指定的 Doc。

在行存储中，有三个重要的概念：
1. chunk: 一堆文档的集合， 每 128 个 doc 会形成一个 chunk， 或者存储的实体数据超过 16k 也会形成一个 chunk; 
2. block: chunk 的集合，1024 个 chunk 组成一个 chunk.
3. slice: 文档的集合，集合有可能跨 chunk 存储

### FDT 文件
fdt 文件格式如下：

![es-fdt](/images/es/es-fdt.jpg "es-fdt")

fdt 文件有以下的特点：
1. 一个 doc 中的所有 stored field 存储到一个 fdt 文件，以 doc 为单位存储在 chunk 中；
2. fdt 按照 chunk 进行存储，每一个 chunk 会维护起始的 docId、每个 doc 的 stored field 数量及每一个文档的长度，方便进行检索定位。

### FDX 文件
fdx 文件格式如下：

![es-fdx](/images/es/es-fdx.jpg "es-fdx")

fdx 文件有以下的特点：
1. 以 block 为单位存储 chunk 的元数据信息，包括 chunk 的地址信息；
2. 每一个 block 维护了 最小 docId、起始地址信息、 所属每一个 chunk 的文档数量及文件指针信息；
3. 通过 2) 提供的信息，可以实现 docId 的二分查找。

fdx 索引文件中存放了两个关键的数组：docBaseDeltas 和 startPointDeltas，分别存储了 chunk 的文档数量及 fdt 文件指针。这两个数组不是存储原始值，而是使用差值算法，计算出平均值和 delta 数组，从而减少数值的范围方便压缩优化，以 [128, 76, 75, 102, 100, 120] 数组为例：
1. 首先计算平均值， 四舍五入得到平均值为 100; 
2. 计算一个 delta 数组，规则见下面的算法，算下来 delta 数组为：[0, 28, 4, -21, -19, -19]
3. 对于 delta 数组，采用 packedInt 进行压缩，生成新的数组；
4. 根据平均值和 delta 数组就可以还原出原始数据。

**delta 数组计算规则：**
```python
base = 0
delta_array = []
for i in range(len(array)):
    delta = base - avg * i
    delta_array.append(delta)
    base += array[i]
```

### 查询算法
根据 fdx 及 fdt 的内容可以方便进行文档的查询，查询方法如下：
1. 根据 docId, 使用每个 block 的 DocBase 二分查找定位文档属于哪个 block; 
2. 然后根据每个 chunk 的 DocBase 二分查找定位文档属于 block 中的哪个 chunk; 
3. 第 n 个 chunk 的 DocID 位置：  DocBase + AvgChunkDocs * n + DocBaseDeltas[n];
4. 得到属于哪个 chunk 之后，就可以通过这个 chunk 的 startPointer (StartPointerDeltachunk 编号) 计算出对应的文件位置；
5. 第 n 个 chunk 的文档指针位置： StartPointerBase + AvgChunkSiez * n + StartPointerDeltas[n].

## 列存储
对于 DocValues 类型的字段来说，使用两种类型的文件进行存储：1) .dvd 文件存储 DocValues 的数据; 2) .dvm 文件存储 DocValues 的元数据，用于解析数据文件； Lucene 支持五种字段的值类型，且针对每种字段值的类型有不同的编码策略，以适应它们的数据特征，这五种类型为：

| 类型 |  描述 |
| ---- | ---- |
| NUMERIC | 单个值的数值类型 |
| BINARY | byte[] 类型 |
| SORTED | 排序的 BINARY 类型，单值 |
| SORTED_SET | 支持多值且有序的 BINARY 类型  |
| SORTED_NUMERIC | 多个值的数值类型 |

DocValues 针对每种字段值的类型有不同的编码策略，以适应它们的数据特征。同样地每一种类型 dvd 及 dvm 文件都会有所不同，我们以最简单的 NUMERIC 为例。

### 整体结构
![es-column-storage](/images/es/es-column-storage.jpg "es-column-storage")

简单来说，列存储主要是将一组 DocIdSet 与 一组字段值建立映射，从而方便进行聚合计算，不同于行存储以 Doc 为单位进行存储，列存储是以 Field 为单位进行存储，可以简单描述为下面的模型：
```json
docIdSet --> values(field1), values(field2)...
```
如果一个 doc 有多个 DocValues 字段的话，每个字段的数据文件都是存储在一个 .dvd 文件上， 索引文件也是同样如此。

### NUMERIC 文件格式
![es-column-numeric](/images/es/es-column-numeric.jpg "es-column-numeric")

**重点字段：**
- DocIdSet 文件指针：第一个 StartFP 存储 IndexedDISI 在 .dvd 文件起始位置的地址。当 DocIDSet 为空或者全量时，Lucene 不需要记录 IndexedDISI，仅在 .dvm 写入 StartFP 特殊标记的值，随后的 Length为 -1（表示 .dvd 文件中没有 IndexedDISI，它原意是指 IndexedDISI 在 .dvd 中的文件大小）；
- IndexedDISI：存储 DocIDSet 数据，如果 DocIDSet 为空或者全量时，则不需要该值；
- ValMetaData：存储了 Values 的编码元数据，不同情况有不同的值；
- NumBitsPerVal：表示存储 Value 需要的位数；
- Min：压缩编码公式 (num-min)/gcd 里面的 min 值。当所有的 docValue 值是一个的时候，就存储那个值；
- GCD：压缩编码公式 (num-min)/gcd 里面的 gcd 值；
- Values 文件指针：最后一个 StartFP 和 Length 存放数据在 .dvd 文件中起始地址和长度。

### GCD-Compression

在 dvm 文件中会存储 Min 及 GCD 字段，这两个字段就涉及到 GCD-Compression。GCD-Compression 是一种数组压缩算法，以数组 [9,6,12,33] 为例，算法如下：
1. 计算出最大公约数 3 (gcd = 3) 和最小值 6(min = 6)；
2. 使用公式遍历数组：(val - min) / gcd, 得到新数组: [1,0,2,9]; 
3. 相比之前，需要 3 个字节存储每一个元素(最大值 33 需要 3 个字节)，新数组只需要 2 个字节(最大值 9 只需要 2 个字节)。

### IndexedDISI 存储格式

存储格式是根据数据集的分布而设定的存储方案，对于 DocIDSet 这种特殊的结构，Lucene 设计了 IndexedDISI 结构，它充分利用了数据集的稀稠性特点。

IndexedDISI 按 65535 的倍数为界将 DocIDSet 分组，故第 n 组的所有 DocIDs 必须在 `65535 * (n-1) ~ 65535 * n` 范围内。当有些文档的字段无值时，便会出现某些组 DocID 的数量不满 65535，当它小于 4096时，Lucene 将它视为稀疏结构用 short[] 存储；反之则是稠密结构用 BitSet 存储。当然所有的 DocID 都存在，则称为全量，那也没必要存储 DocIDSet 了，仅写一个 Flag 来表示即可。

BitSet 的存储空间复杂度由它的最大值唯一决定，那么数据集比较小而最大值比较大时，这种方案存储代价会比较高的。而对于 short[] 而言，它的存储复杂度是随数量的增长呈正相关，而 4096 这个数值是 BitSet 与short[] 存储复杂度的分水岭。小于则是稀疏的 short[] 结构，否则则是稠密的 BitSet 结构。

另外，DocIDSet 的所有 DocID 都存在时，DocIDSet 可以省略，通过在 dvm 文件写入一个 Flag 值表示全量，因此这种情况不需要在 dvd 文件上写入任何内容。

## 总结
在 Lucene 中根据数据的特点采用不同的存储模式及压缩算法，正是有了这些优化的策略，使得基于 Lucene 的 Elasticsearch 应用天然就继承了这些优点，使得 Elasticsearch 有了更为广阔的使用场景。

</br>

**参考：**

----
[1]:https://zhuanlan.zhihu.com/p/35469104
[2]:https://zhuanlan.zhihu.com/p/34680841
[3]:https://www.cnblogs.com/tgzhu/p/14435684.html
[4]:https://zhuanlan.zhihu.com/p/384486147
[5]:https://cloud.tencent.com/developer/article/1361270
[6]:https://cloud.tencent.com/developer/article/1370303?from=article.detail.1361270
[7]:https://zhuanlan.zhihu.com/p/384487150
[8]:http://www.nosqlnotes.com/technotes/searchengine/lucene-docvalues/



[1.Lucene解析 - 基本概念][1]

[2.Elasticsearch内核解析 - 数据模型篇][2]

[3.R2_ES中数据的存储测试][3]

[4.Lucene源码解析——StoredField存储方式][4]

[5.Elasitcsearch 底层系列 Lucene 内核解析之 Stored Fields][5]

[6.Elasitcsearch 底层系列 Lucene 内核解析之 Doc Value][6]

[7.Lucene源码解析——DocValue存储方式][7]

[8.Lucene列式存储格式DocValues详解][7]