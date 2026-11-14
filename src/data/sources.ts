import { DataSourceEntry } from "./types";

export const DATA_SOURCES: DataSourceEntry[] = [
  {
    id: "src-osm",
    category: "公开地理矢量底图",
    name: "OpenStreetMap（Overpass API 东城区片区实测轮廓）",
    coverage:
      "西校区边界（way 352521262）、主教学综合楼（way 398697589）、南弧面楼（way 636389217）、东校区南院（way 398694728）、南主及配楼（ways 477977120–477977123）、双联篮球场（838569683–838569684）",
    licenseOrNote: "ODbL 开放数据库许可 · 已转换为 ENU 局部米制工程坐标",
    url: "https://www.openstreetmap.org/",
  },
  {
    id: "src-esri",
    category: "高分辨率正射影像参考",
    name: "Esri World Imagery（Zoom-19 航拍正射瓦片对照校验）",
    coverage:
      "屋面材质颜色（西翼 C 座 3×5 金字塔采光天窗、北区白色弧顶主席台、东校区绿色屋顶涂层及北院四合院红砖道走向校验）",
    licenseOrNote: "仅用于本地三维比例与屋顶平面形态校核，不重新分发第三方专有瓦片",
  },
  {
    id: "src-bj166site",
    category: "公开校园实景照片参照",
    name: "bj166-school-site（ibb-official 公开静态图文存档）",
    coverage:
      "同福夹道南正门 2020/2024 立面对比、东四六条甲44号北正门、室外弧形大坡道、外挂折返楼梯塔、慎独石、操场张拉膜主席台",
    licenseOrNote: "仅收录公开新闻与建筑外观实拍照片，已排查剔除学生正面人像及敏感区域",
    url: "https://bj166zx.cn",
  },
  {
    id: "src-bjnews",
    category: "公开媒体报道资料",
    name: "新京报公开校园建设及160周年校庆新闻报道",
    coverage:
      "西校区室外弧形坡道（雪松与红色花箱）、B座/D座红色书本牌匾、校园百草园与音乐长廊空间功能校核",
    licenseOrNote: "仅供校园公共空间建筑细节对照参考",
  },
];
