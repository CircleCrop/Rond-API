# Rond 数据库结构文档

- **数据库来源**：`tests/LifeEasy.sqlite`（Core Data + CloudKit 同步）
- **只读约束**：API 仅做只读访问，打开时 Rond App 可能正在写入
- **时间基准**：所有 `TIMESTAMP` / `FLOAT` 时间字段均为 **Core Data NSDate**（自 2001-01-01 00:00:00 UTC 的秒数），转 Unix 时间戳需 `+978307200`

---

## 目录

### 核心业务表

| 表名 | 实体 | 说明 | 行数 |
| --- | --- | --- | --- |
| [ZVISIT](#zvisit) | Visit | 到访记录（核心） | ~1828 |
| [ZLOCATION](#zlocation) | Location | 地点 | ~858 |
| [ZMOVEMENT](#zmovement) | Movement | 两次到访之间的移动 | ~1223 |
| [ZRAWVISIT](#zrawvisit) | RawVisit | CLVisit 原始数据 | ~3106 |
| [ZACTIVITY](#zactivity) | Activity | 活动类型（餐厅、健身…） | 30 |
| [ZTRANSPORT](#ztransport) | Transport | 交通方式（地铁、步行…） | 6 |
| [ZTAG](#ztag) | Tag | 用户标签 | 5 |
| [ZTAGGROUP](#ztaggroup) | TagGroup | 标签分组 | 1 |
| [ZTRIP](#ztrip) | Trip | 行程 | 4 |
| [ZTRIPDAY](#ztripday) | TripDay | 行程的单日 | 0 |
| [ZTRIPSEGMENT](#ztripsegment) | TripSegment | 行程片段 | 0 |
| [ZJOURNAL](#zjournal) | Journal | 日记 | 1 |
| [ZKEYWORD](#zkeyword) | Keyword | 关键词（自动匹配规则） | 2 |
| [ZPOICATEGORY](#zpoicategory) | PoiCategory | Apple MapKit POI 类别 → 活动映射 | 30 |
| [ZHOURLYWEATHER](#zhourlyweather) | HourlyWeather | 到访时段的小时天气 | ~2313 |
| [ZSTAYSEGMENT](#zstaysegment) | StaySegment | 到访内的停留子段 | 9 |
| [ZUSERPHOTO](#zuserphoto) | UserPhoto | 用户照片引用 | 0 |

### 多对多关联表

| 表名 | 关系 |
| --- | --- |
| [Z_1TAGS\_](#z_1tags_) | Activity ↔ Tag |
| [Z_4TAGS\_](#z_4tags_) | Keyword ↔ Tag |
| [Z_5TAGS\_](#z_5tags_) | Location ↔ Tag |
| [Z_8TAGS\_](#z_8tags_) | RawVisit ↔ Tag |
| [Z_10VISITS\_](#z_10visits_) | Tag ↔ Visit |
| [Z_10TRIPS\_](#z_10trips_) | Tag ↔ Trip |

### Core Data / CloudKit 内部表

| 表名 | 用途 |
| --- | --- |
| [Z_PRIMARYKEY](#z_primarykey) | 实体 ID → 名称映射 & 主键计数器 |
| [Z_METADATA](#z_metadata) | Core Data 存储版本与 UUID |
| [Z_MODELCACHE](#z_modelcache) | Core Data 模型缓存 |
| [ATRANSACTION](#atransaction) | Core Data 持久化历史事务 |
| [ATRANSACTIONSTRING](#atransactionstring) | 事务字符串池 |
| [ACHANGE](#achange) | 持久化历史变更记录 |
| ANSCK* | CloudKit 同步元数据（详见末尾） |

---

## 核心业务表

### ZVISIT

**到访记录** — 应用的核心数据，每条记录代表用户在某个地点的一次停留。

| 列名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| Z_PK | INTEGER | 否 | 主键 |
| Z_ENT | INTEGER | 否 | Core Data 实体类型（固定 = 17） |
| Z_OPT | INTEGER | 否 | Core Data 乐观锁版本号 |
| ZBOOKMARKED | INTEGER | 是 | 是否收藏（0/1） |
| ZISKEYWORDRULEDISMISSED | INTEGER | 是 | 关键词自动匹配规则是否被用户忽略 |
| ZISPHOTOIMPORT | INTEGER | 是 | 是否来自照片位置导入（0/1） |
| ZISPLACETAGEXCLUDED | INTEGER | 是 | 是否排除地点标签自动关联 |
| ZUSERADDED | INTEGER | 是 | 是否用户手动添加（0/1） |
| ZUSERIGNORED | INTEGER | 是 | 是否被用户忽略（0/1） |
| ZACTIVITY_ | INTEGER | 是 | → ZACTIVITY.Z_PK，活动类型 |
| ZLOCATION | INTEGER | 是 | → ZLOCATION.Z_PK，关联地点 |
| ZMERGEDTO | INTEGER | 是 | → ZVISIT.Z_PK，合并目标（被合并到另一条到访） |
| ZPARENT | INTEGER | 是 | → ZVISIT.Z_PK，父到访（用于嵌套到访） |
| ZRAW | INTEGER | 是 | → ZRAWVISIT.Z_PK，原始 CLVisit 数据 |
| ZTRIPSEGMENT_ | INTEGER | 是 | → ZTRIPSEGMENT.Z_PK，所属行程片段 |
| ZARRIVALDATE_ | TIMESTAMP | 是 | 到达时间（NSDate） |
| ZDEPARTUREDATE_ | TIMESTAMP | 是 | 离开时间（NSDate） |
| ZEVENTIDENTIFIER | VARCHAR | 是 | 日历事件标识符 |
| ZREMARK_ | VARCHAR | 是 | 用户备注 |
| ZTIMEZONEIDENTIFIER | VARCHAR | 是 | 时区标识（如 `UTC`） |
| ZWEATHERSYMBOL_ | VARCHAR | 是 | SF Symbols 天气图标名 |
| ZIDENTIFIER_ | BLOB | 是 | 唯一标识（UUID 二进制） |
| ZEMOJINAME_ | VARCHAR | 是 | Emoji 名称（如 `neutralFace`） |
| ZASSOCIATIONBITMASK_ | INTEGER | 是 | 关联掩码（预留，当前全为 0） |

---

### ZLOCATION

**地点** — 地理位置信息，包含坐标、行政区划、Apple MapKit 匹配结果。

| 列名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| Z_PK | INTEGER | 否 | 主键 |
| Z_ENT | INTEGER | 否 | Core Data 实体类型（固定 = 5） |
| Z_OPT | INTEGER | 否 | Core Data 乐观锁版本号 |
| ZBOOKMARKED | INTEGER | 是 | 是否收藏 |
| ZISLIVEACTIVITYENABLED | INTEGER | 是 | 是否启用实时活动（灵动岛） |
| ZISPHOTOIMPORT | INTEGER | 是 | 是否来自照片导入（0/1） |
| ZMINMINUTES_ | INTEGER | 是 | 最小停留分钟数（地理围栏触发阈值） |
| ZNEEDREFRESH | INTEGER | 是 | 是否需要重新匹配/刷新地点信息 |
| ZPINSTYLE_ | INTEGER | 是 | 图钉样式（UI 显示） |
| ZTYPE_ | INTEGER | 是 | 地点类型：0=普通，1=家/工作，2=其他，3=特殊 |
| ZUSERADDED | INTEGER | 是 | 是否用户手动添加 |
| ZUSERIGNORED | INTEGER | 是 | 是否被用户忽略 |
| ZUSERACTIVITY_ | INTEGER | 是 | → ZACTIVITY.Z_PK，用户指定的活动类型 |
| ZCOUNTDOWNINSECONDS | FLOAT | 是 | 倒计时秒数（计时器功能） |
| ZLASTARRIVALDATE_ | TIMESTAMP | 是 | 最近一次到达时间 |
| ZLATITUDE | FLOAT | 是 | 纬度 |
| ZLONGITUDE | FLOAT | 是 | 经度 |
| ZRADIUS | FLOAT | 是 | 地理围栏半径（米） |
| ZRATING | FLOAT | 是 | 评分 |
| ZADMINISTRATIVEAREA | VARCHAR | 是 | 省/州（如 `江苏省`） |
| ZCATEGORY_ | VARCHAR | 是 | 自定义类别 |
| ZISOCOUNTRYCODE | VARCHAR | 是 | ISO 国家代码（如 `CN`） |
| ZLOCALITY | VARCHAR | 是 | 城市 |
| ZNAME_ | VARCHAR | 是 | 地点名称 |
| ZNOTE_ | VARCHAR | 是 | 用户备注 |
| ZPLACEID | VARCHAR | 是 | Apple MapKit Place ID |
| ZSUBADMINISTRATIVEAREA | VARCHAR | 是 | 区县 |
| ZSUBLOCALITY | VARCHAR | 是 | 街道/社区 |
| ZSUBTHOROUGHFARE | VARCHAR | 是 | 门牌号 |
| ZTHOROUGHFARE | VARCHAR | 是 | 道路名 |
| ZTIMEZONE | VARCHAR | 是 | 时区 |

---

### ZMOVEMENT

**移动记录** — 两次到访之间的移动路径，表示从一个地点前往另一个地点。

| 列名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| Z_PK | INTEGER | 否 | 主键 |
| Z_ENT | INTEGER | 否 | Core Data 实体类型（固定 = 6） |
| Z_OPT | INTEGER | 否 | Core Data 乐观锁版本号 |
| ZISMODIFIED | INTEGER | 是 | 是否被用户手动修改 |
| ZTYPE_ | INTEGER | 是 | 移动类型：0=未知，2=步行，3=跑步，4=驾车，5=公共交通，6=骑行 |
| ZTRANSPORT_ | INTEGER | 是 | → ZTRANSPORT.Z_PK，交通方式（自定义） |
| ZVISITFROM_ | INTEGER | 是 | → ZVISIT.Z_PK，出发地到访 |
| ZVISITTO_ | INTEGER | 是 | → ZVISIT.Z_PK，目的地到访 |
| ZEND_ | TIMESTAMP | 是 | 移动结束时间 |
| ZSTART_ | TIMESTAMP | 是 | 移动开始时间 |
| ZNOTE_ | VARCHAR | 是 | 用户备注 |

---

### ZRAWVISIT

**原始到访** — 来自 iOS CLVisit（Core Location）的未加工数据，由系统自动采集。

| 列名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| Z_PK | INTEGER | 否 | 主键 |
| Z_ENT | INTEGER | 否 | Core Data 实体类型（固定 = 8） |
| Z_OPT | INTEGER | 否 | Core Data 乐观锁版本号 |
| ZISMODIFIED | INTEGER | 是 | 是否被用户修改 |
| ZNEEDREFRESH | INTEGER | 是 | 是否需重新处理 |
| ZACTIVITY | INTEGER | 是 | → ZACTIVITY.Z_PK，匹配的活动类型 |
| ZLOCATION | INTEGER | 是 | → ZLOCATION.Z_PK，匹配的地点 |
| ZVISIT | INTEGER | 是 | → ZVISIT.Z_PK，归属的到访记录 |
| ZACCURACY | FLOAT | 是 | 定位精度（米） |
| ZARRIVALDATE_ | TIMESTAMP | 是 | CLVisit 到达时间 |
| ZDEPARTUREDATE_ | TIMESTAMP | 是 | CLVisit 离开时间（未离开时为极大值 63113904000） |
| ZLATITUDE | FLOAT | 是 | 纬度 |
| ZLONGITUDE | FLOAT | 是 | 经度 |
| ZNOTIFIEDDATE_ | TIMESTAMP | 是 | 通知触发时间 |
| ZTIMERNOTIFICATIONDATE_ | TIMESTAMP | 是 | 计时器通知时间 |
| ZADMINISTRATIVEAREA | VARCHAR | 是 | 省/州 |
| ZDETAIL | VARCHAR | 是 | CLVisit 详细调试信息（含原始坐标、置信度等） |
| ZISOCOUNTRYCODE | VARCHAR | 是 | ISO 国家代码 |
| ZLOCALITY | VARCHAR | 是 | 城市 |
| ZNAME | VARCHAR | 是 | 反向地理编码地名 |
| ZNOTE_ | VARCHAR | 是 | 用户备注 |
| ZSUBADMINISTRATIVEAREA | VARCHAR | 是 | 区县 |
| ZSUBLOCALITY | VARCHAR | 是 | 街道 |
| ZSUBTHOROUGHFARE | VARCHAR | 是 | 门牌号 |
| ZTHOROUGHFARE | VARCHAR | 是 | 道路名 |
| ZTIMEZONE | VARCHAR | 是 | 时区 |

---

### ZACTIVITY

**活动类型** — 预定义的到访活动分类，如「餐厅」「健身」「商场」等。

| 列名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| Z_PK | INTEGER | 否 | 主键 |
| Z_ENT | INTEGER | 否 | Core Data 实体类型（固定 = 1） |
| Z_OPT | INTEGER | 否 | Core Data 乐观锁版本号 |
| ZISARCHIVED | INTEGER | 是 | 是否归档（隐藏但不删除） |
| ZISCALENDAREXCLUDED | INTEGER | 是 | 是否从日历中排除 |
| ZISDEFAULT | INTEGER | 是 | 是否为默认活动类型 |
| ZISEXCLUDED | INTEGER | 是 | 是否总体排除（不参与统计） |
| ZISHOME | INTEGER | 是 | 是否为「家」 |
| ZISWORK | INTEGER | 是 | 是否为「工作」 |
| ZPINSTYLE_ | INTEGER | 是 | 图钉样式 |
| ZCR_ | FLOAT | 是 | 自定义颜色 R 分量（0~1） |
| ZCG_ | FLOAT | 是 | 自定义颜色 G 分量 |
| ZCB_ | FLOAT | 是 | 自定义颜色 B 分量 |
| ZCA_ | FLOAT | 是 | 自定义颜色 Alpha 分量 |
| ZG_ | FLOAT | 是 | 自定义颜色灰度分量（备用） |
| ZLASTARRIVALDATE_ | TIMESTAMP | 是 | 最近一次该活动到达时间 |
| ZCALENDARIDENTIFIER | VARCHAR | 是 | 日历标识符 |
| ZCOLOR_ | VARCHAR | 是 | 预设颜色名（如 `purple`、`orange`）；若为 nil 则使用 RGBA 分量 |
| ZICON_ | VARCHAR | 是 | SF Symbols 图标名（如 `dumbbell.fill`） |
| ZNAME_ | VARCHAR | 是 | 活动名称（如「健身」「餐厅」） |
| ZUID_ | BLOB | 是 | 唯一标识（UUID 二进制） |

---

### ZTRANSPORT

**交通方式** — 用户自定义的交通方式。

| 列名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| Z_PK | INTEGER | 否 | 主键 |
| Z_ENT | INTEGER | 否 | Core Data 实体类型（固定 = 12） |
| Z_OPT | INTEGER | 否 | Core Data 乐观锁版本号 |
| ZISDEFAULT | INTEGER | 是 | 是否为默认交通方式 |
| ZCOLOR_ | VARCHAR | 是 | 显示颜色 |
| ZICON_ | VARCHAR | 是 | SF Symbols 图标名（如 `lightrail.fill`） |
| ZNAME_ | VARCHAR | 是 | 名称（如「地铁」「電車」） |

---

### ZTAG

**标签** — 用户创建的标签，可关联到到访、地点、活动等多种实体。

| 列名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| Z_PK | INTEGER | 否 | 主键 |
| Z_ENT | INTEGER | 否 | Core Data 实体类型（固定 = 10） |
| Z_OPT | INTEGER | 否 | Core Data 乐观锁版本号 |
| ZISARCHIVED | INTEGER | 是 | 是否归档 |
| ZISAUTOMARK | INTEGER | 是 | 是否自动标记（规则驱动） |
| ZPINSTYLE_ | INTEGER | 是 | 图钉样式 |
| ZGROUP | INTEGER | 是 | → ZTAGGROUP.Z_PK，所属分组 |
| ZLASTARRIVALDATE_ | TIMESTAMP | 是 | 最近一次使用该标签的到访时间 |
| ZCOLOR_ | VARCHAR | 是 | 显示颜色（如 `red`、`pink`） |
| ZNAME_ | VARCHAR | 是 | 标签名（如「中传」「南昌融创」） |

---

### ZTAGGROUP

**标签分组** — 对标签进行逻辑分组。

| 列名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| Z_PK | INTEGER | 否 | 主键 |
| Z_ENT | INTEGER | 否 | Core Data 实体类型（固定 = 11） |
| Z_OPT | INTEGER | 否 | Core Data 乐观锁版本号 |
| ZNAME_ | VARCHAR | 是 | 分组名称（如「朋友」） |

---

### ZTRIP

**行程** — 用户创建的旅行/行程记录。

| 列名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| Z_PK | INTEGER | 否 | 主键 |
| Z_ENT | INTEGER | 否 | Core Data 实体类型（固定 = 13） |
| Z_OPT | INTEGER | 否 | Core Data 乐观锁版本号 |
| ZDAYCOUNT | INTEGER | 是 | 行程天数 |
| ZISALLDAY | INTEGER | 是 | 是否为全天行程 |
| ZSHOWDAILYMAP | INTEGER | 是 | 是否显示每日地图 |
| ZSHOWDAILYNOTE | INTEGER | 是 | 是否显示每日备注 |
| ZSHOWDAILYPHOTOS | INTEGER | 是 | 是否显示每日照片 |
| ZSHOWTAGS | INTEGER | 是 | 是否显示标签 |
| ZSHOWTRANSPORTATION | INTEGER | 是 | 是否显示交通方式 |
| ZENDDATE_ | TIMESTAMP | 是 | 行程结束时间 |
| ZSTARTDATE_ | TIMESTAMP | 是 | 行程开始时间 |
| ZNOTE_ | VARCHAR | 是 | 备注 |
| ZTIMEZONE_ | VARCHAR | 是 | 时区 |
| ZTITLE_ | VARCHAR | 是 | 行程标题 |

---

### ZTRIPDAY

**行程日** — 行程内的单日记录。

| 列名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| Z_PK | INTEGER | 否 | 主键 |
| Z_ENT | INTEGER | 否 | Core Data 实体类型（固定 = 14） |
| Z_OPT | INTEGER | 否 | Core Data 乐观锁版本号 |
| ZPARENT_ | INTEGER | 是 | → ZTRIP.Z_PK，所属行程 |
| ZSTARTOFDAY_ | TIMESTAMP | 是 | 该日开始时间 |
| ZNOTE_ | VARCHAR | 是 | 日备注 |

---

### ZTRIPSEGMENT

**行程片段** — 行程中的一个阶段，可包含多个到访。

| 列名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| Z_PK | INTEGER | 否 | 主键 |
| Z_ENT | INTEGER | 否 | Core Data 实体类型（固定 = 15） |
| Z_OPT | INTEGER | 否 | Core Data 乐观锁版本号 |
| ZPARENT_ | INTEGER | 是 | → ZTRIPDAY.Z_PK，所属行程日 |
| ZNOTE_ | VARCHAR | 是 | 备注 |
| ZTITLE_ | VARCHAR | 是 | 片段标题 |

---

### ZJOURNAL

**日记** — 用户写的日记条目。

| 列名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| Z_PK | INTEGER | 否 | 主键 |
| Z_ENT | INTEGER | 否 | Core Data 实体类型（固定 = 3） |
| Z_OPT | INTEGER | 否 | Core Data 乐观锁版本号 |
| ZASSOCIATIONBITMASK_ | INTEGER | 是 | 关联类型掩码（标记与哪些实体关联） |
| ZBOOKMARKED | INTEGER | 是 | 是否收藏 |
| ZDATE_ | TIMESTAMP | 是 | 日记日期 |
| ZUPDATEDATE_ | TIMESTAMP | 是 | 最后更新时间 |
| ZCONTENT_ | VARCHAR | 是 | 日记正文 |
| ZEMOJINAME_ | VARCHAR | 是 | 心情 Emoji 名（如 `neutralFace`） |
| ZTITLE_ | VARCHAR | 是 | 标题 |

---

### ZKEYWORD

**关键词** — 绑定到活动类型的自动匹配关键词，当地点名包含该关键词时自动归类。

| 列名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| Z_PK | INTEGER | 否 | 主键 |
| Z_ENT | INTEGER | 否 | Core Data 实体类型（固定 = 4） |
| Z_OPT | INTEGER | 否 | Core Data 乐观锁版本号 |
| ZACTIVITY_ | INTEGER | 是 | → ZACTIVITY.Z_PK，关联的活动类型 |
| ZDATEADDED_ | TIMESTAMP | 是 | 添加时间 |
| ZCONTENT_ | VARCHAR | 是 | 关键词内容（如「瑞幸」→ 活动「茶饮」） |

---

### ZPOICATEGORY

**POI 类别映射** — Apple MapKit POI 类别到 Rond 活动类型的映射规则。

| 列名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| Z_PK | INTEGER | 否 | 主键 |
| Z_ENT | INTEGER | 否 | Core Data 实体类型（固定 = 7） |
| Z_OPT | INTEGER | 否 | Core Data 乐观锁版本号 |
| ZACTIVITY_ | INTEGER | 是 | → ZACTIVITY.Z_PK，映射到的活动类型 |
| ZRAWVALUE | VARCHAR | 是 | MapKit POI 类别原始值（如 `MKPOICategoryRestaurant` → 餐厅） |

---

### ZHOURLYWEATHER

**小时天气** — 到访时段对应的逐小时气象数据（来自 WeatherKit）。

| 列名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| Z_PK | INTEGER | 否 | 主键 |
| Z_ENT | INTEGER | 否 | Core Data 实体类型（固定 = 2） |
| Z_OPT | INTEGER | 否 | Core Data 乐观锁版本号 |
| ZISDAYLIGHT | INTEGER | 是 | 是否为白天 |
| ZUVINDEXVALUE_ | INTEGER | 是 | UV 指数值 |
| ZVISIT | INTEGER | 是 | → ZVISIT.Z_PK，关联的到访 |
| ZAPPARENTTEMPERATURE_ | FLOAT | 是 | 体感温度（开尔文） |
| ZDATE_ | TIMESTAMP | 是 | 该小时对应的时间 |
| ZDEWPOINT_ | FLOAT | 是 | 露点温度（开尔文） |
| ZHUMIDITY_ | FLOAT | 是 | 相对湿度（0~1） |
| ZPRECIPITATIONAMOUNT_ | FLOAT | 是 | 降水量（mm） |
| ZPRECIPITATIONCHANCE_ | FLOAT | 是 | 降水概率（0~1） |
| ZTEMPERATURE_ | FLOAT | 是 | 温度（开尔文） |
| ZVISIBILITY_ | FLOAT | 是 | 能见度（米） |
| ZWINDSPEED_ | FLOAT | 是 | 风速（km/h） |
| ZCONDITION_ | VARCHAR | 是 | 天气状况（如 `mostlyClear`、`windy`） |
| ZPRECIPITATION_ | VARCHAR | 是 | 降水类型（如 `none`、`rain`） |
| ZSYMBOLNAME_ | VARCHAR | 是 | SF Symbols 天气图标（如 `sun.max`、`cloud`） |
| ZUVINDEXCATEGORY_ | VARCHAR | 是 | UV 等级（如 `high`、`moderate`） |
| ZWINDCOMPASSDIRECTION_ | VARCHAR | 是 | 风向（如 `northwest`） |

---

### ZSTAYSEGMENT

**停留子段** — 一次到访内经过的多个地点子段（在不离开到访的情况下移动到附近地点）。

| 列名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| Z_PK | INTEGER | 否 | 主键 |
| Z_ENT | INTEGER | 否 | Core Data 实体类型（固定 = 9） |
| Z_OPT | INTEGER | 否 | Core Data 乐观锁版本号 |
| ZLOCATION | INTEGER | 是 | → ZLOCATION.Z_PK，子段所在地点 |
| ZPARENTVISIT | INTEGER | 是 | → ZVISIT.Z_PK，所属到访 |
| ZADDEDAT_ | TIMESTAMP | 是 | 添加时间 |

---

### ZUSERPHOTO

**用户照片** — 关联到到访/行程/日记的照片引用。

| 列名 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| Z_PK | INTEGER | 否 | 主键 |
| Z_ENT | INTEGER | 否 | Core Data 实体类型（固定 = 16） |
| Z_OPT | INTEGER | 否 | Core Data 乐观锁版本号 |
| ZJOURNAL_ | INTEGER | 是 | → ZJOURNAL.Z_PK，关联日记 |
| ZTRIPDAY_ | INTEGER | 是 | → ZTRIPDAY.Z_PK，关联行程日 |
| ZTRIP_ | INTEGER | 是 | → ZTRIP.Z_PK，关联行程 |
| ZVISIT_ | INTEGER | 是 | → ZVISIT.Z_PK，关联到访 |
| ZADDEDAT_ | TIMESTAMP | 是 | 添加时间 |
| ZPATH_ | VARCHAR | 是 | 照片路径（应用内相对路径） |

---

## 多对多关联表

Core Data 自动生成的多对多中间表，命名规则：`Z_{源实体ENT编号}{关系名}_`。

### Z_1TAGS_

**Activity ↔ Tag**

| 列名 | 类型 | 说明 |
| --- | --- | --- |
| Z_1ACTIVITIES_ | INTEGER | → ZACTIVITY.Z_PK |
| Z_10TAGS_ | INTEGER | → ZTAG.Z_PK |

### Z_4TAGS_

**Keyword ↔ Tag**

| 列名 | 类型 | 说明 |
| --- | --- | --- |
| Z_4KEYWORDS_ | INTEGER | → ZKEYWORD.Z_PK |
| Z_10TAGS_1 | INTEGER | → ZTAG.Z_PK |

### Z_5TAGS_

**Location ↔ Tag**

| 列名 | 类型 | 说明 |
| --- | --- | --- |
| Z_5LOCATIONS_ | INTEGER | → ZLOCATION.Z_PK |
| Z_10TAGS_2 | INTEGER | → ZTAG.Z_PK |

### Z_8TAGS_

**RawVisit ↔ Tag**

| 列名 | 类型 | 说明 |
| --- | --- | --- |
| Z_8RAWVISITS_ | INTEGER | → ZRAWVISIT.Z_PK |
| Z_10TAGS_3 | INTEGER | → ZTAG.Z_PK |

### Z_10VISITS_

**Tag ↔ Visit**

| 列名 | 类型 | 说明 |
| --- | --- | --- |
| Z_10TAGS_5 | INTEGER | → ZTAG.Z_PK |
| Z_17VISITS_ | INTEGER | → ZVISIT.Z_PK |

### Z_10TRIPS_

**Tag ↔ Trip**

| 列名 | 类型 | 说明 |
| --- | --- | --- |
| Z_10TAGS_4 | INTEGER | → ZTAG.Z_PK |
| Z_13TRIPS_ | INTEGER | → ZTRIP.Z_PK |

---

## Core Data 内部表

### Z_PRIMARYKEY

**实体主键计数器** — 记录每个 Core Data 实体的名称和当前最大主键值。

| 列名 | 类型 | 说明 |
| --- | --- | --- |
| Z_ENT | INTEGER | 实体编号（1~17 为业务实体；16001~16003 为历史追踪；17001~17018 为 CloudKit 同步） |
| Z_NAME | VARCHAR | 实体名称（如 `Visit`、`Location`） |
| Z_SUPER | INTEGER | 父实体编号（0 = 无继承） |
| Z_MAX | INTEGER | 当前最大 Z_PK 值 |

### Z_METADATA

**Core Data 存储元数据**

| 列名 | 类型 | 说明 |
| --- | --- | --- |
| Z_VERSION | INTEGER | 模型版本 |
| Z_UUID | VARCHAR(255) | 存储唯一标识 |
| Z_PLIST | BLOB | 完整元数据 plist |

### Z_MODELCACHE

**Core Data 模型缓存**

| 列名 | 类型 | 说明 |
| --- | --- | --- |
| Z_CONTENT | BLOB | 编译后的 Core Data 模型二进制 |

---

## Core Data 持久化历史表

### ATRANSACTION

**事务记录** — Core Data 持久化历史追踪的事务。

| 列名 | 类型 | 说明 |
| --- | --- | --- |
| Z_PK | INTEGER | 主键 |
| Z_ENT | INTEGER | 实体类型（16002） |
| Z_OPT | INTEGER | 版本号 |
| ZAUTHORTS | INTEGER | 作者字符串池引用 |
| ZBUNDLEIDTS | INTEGER | Bundle ID 字符串池引用 |
| ZCONTEXTNAMETS | INTEGER | Context 名称字符串池引用 |
| ZPROCESSIDTS | INTEGER | 进程 ID 字符串池引用 |
| ZTIMESTAMP | FLOAT | 事务时间戳 |
| ZAUTHOR | VARCHAR | 作者标识 |
| ZBUNDLEID | VARCHAR | 执行写入的 App Bundle ID |
| ZCONTEXTNAME | VARCHAR | NSManagedObjectContext 名称 |
| ZPROCESSID | VARCHAR | 进程 ID |
| ZQUERYGEN | BLOB | 查询 generation token |

### ATRANSACTIONSTRING

**事务字符串池** — 事务元数据中重复字符串的去重存储。

| 列名 | 类型 | 说明 |
| --- | --- | --- |
| Z_PK | INTEGER | 主键 |
| Z_ENT | INTEGER | 实体类型（16003） |
| Z_OPT | INTEGER | 版本号 |
| ZNAME | VARCHAR | 字符串值 |

### ACHANGE

**变更记录** — 持久化历史中的单条变更。

| 列名 | 类型 | 说明 |
| --- | --- | --- |
| Z_PK | INTEGER | 主键 |
| Z_ENT | INTEGER | 实体类型（16001） |
| Z_OPT | INTEGER | 版本号 |
| ZCHANGETYPE | INTEGER | 变更类型（插入/更新/删除） |
| ZENTITY | INTEGER | 受影响的实体类型 Z_ENT |
| ZENTITYPK | INTEGER | 受影响记录的 Z_PK |
| ZTRANSACTIONID | INTEGER | → ATRANSACTION.Z_PK |
| ZCOLUMNS | BLOB | 变更涉及的列（位图） |

---

## CloudKit 同步表（ANSCK*）

以下表由 `NSCloudKitContainer` 框架自动维护，用于 iCloud 同步状态追踪。**API 开发中通常不需要直接读取**。

| 表名 | 说明 |
| --- | --- |
| ANSCKDATABASEMETADATA | CloudKit 数据库范围元数据（数据库名、同步令牌） |
| ANSCKEVENT | CloudKit 同步事件日志（开始/结束/是否成功） |
| ANSCKEXPORTEDOBJECT | 待导出到 CloudKit 的对象 |
| ANSCKEXPORTMETADATA | 导出操作元数据 |
| ANSCKEXPORTOPERATION | 导出操作状态 |
| ANSCKHISTORYANALYZERSTATE | 历史分析器状态（追踪哪些变更已处理） |
| ANSCKIMPORTOPERATION | CloudKit 导入操作记录 |
| ANSCKIMPORTPENDINGRELATIONSHIP | 导入时待建立的关系 |
| ANSCKMETADATAENTRY | 通用键值元数据 |
| ANSCKMIRROREDRELATIONSHIP | 镜像关系（跨设备同步的关系） |
| ANSCKMIRROREDRELATIONSHIPSYSTEMFIELDSASSET | 镜像关系系统字段资产 |
| ANSCKRECORDMETADATA | CKRecord 元数据（每条业务记录的同步状态） |
| ANSCKRECORDMETADATAENCODEDRECORDASSET | CKRecord 编码数据资产 |
| ANSCKRECORDMETADATASYSTEMFIELDSASSET | CKRecord 系统字段资产 |
| ANSCKRECORDZONEMETADATA | Record Zone 元数据（分区同步令牌等） |
| ANSCKRECORDZONEMETADATAENCODEDSHAREASSET | Zone 共享编码资产 |
| ANSCKRECORDZONEMOVERECEIPT | Zone 移动回执 |
| ANSCKRECORDZONEQUERY | Zone 查询状态 |

---

## 实体关系图

```
Trip ──< TripDay ──< TripSegment ──< Visit
                                       │
                    ┌──────────────────┤
                    │                  │
              RawVisit             Location ──── UserActivity → Activity
                    │                  │
                    └── StaySegment ───┘
                                       │
Visit ─── Activity                     │
  │                              PoiCategory → Activity
  ├── Movement (from/to)
  │       └── Transport
  ├── HourlyWeather
  ├── Journal
  └── UserPhoto

Tag ↔ Visit / Location / Activity / Keyword / RawVisit / Trip
  └── TagGroup

Keyword → Activity
```
