# 4.13 全界面主题提案

本提案只从已读PRODUCT/DESIGN和当前CSS事实出发。没有把token计算当成浏览器验收，也没有改动任务、数据库、提醒、导入或备份协议。

## 方向

用户指出的“只换强调色”是代码事实：当前8条data-accent规则只覆盖primary、hover、on-primary、active、focus；page/sidebar/content/field/chrome是共同固定值。必须替换这一结构。

默认Iris采用冷调索引夹的深封面与浅页关系：深墨紫导航是稳定的范围锚点，雾紫底面承接工作区，稍亮但仍带色的内容面呈现真实任务，输入面低一阶，菜单和对话框才用最高亮度。没有伪纸纹、织物图、渐变光晕或成排空卡片。操作仍采用平台无衬线与熟悉控件。

四套主题不是把同一个白界面调primary，而是完整改变这五个大面。浅色下也不使用纯白作为常驻主内容面；最浅raised仅服务短时菜单/对话框。暗色分别按色系设计抬升，不机械反色。

## 八套主面色

| 主题 | 模式 | Canvas | 深导航 | Header | Content | Inset | Raised |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 雾紫 / Iris | light | `#DDDCE7` | `#312D48` | `#D3D2E0` | `#EEEFF5` | `#E4E4ED` | `#F9F8FC` |
| 雾紫 / Iris | dark | `#211E2E` | `#191724` | `#292536` | `#2D2A3B` | `#242132` | `#373246` |
| 海湾 / Ocean | light | `#D8E4E9` | `#213B48` | `#CBDDE4` | `#EBF2F5` | `#DDE9EF` | `#F6FAFC` |
| 海湾 / Ocean | dark | `#182C37` | `#12232C` | `#1D3542` | `#233E4C` | `#1B3240` | `#2E4B59` |
| 松林 / Pine | light | `#DCE6DF` | `#243C36` | `#CDDDD2` | `#EDF3ED` | `#DFEADF` | `#F7FBF6` |
| 松林 / Pine | dark | `#1C3027` | `#14261F` | `#233D30` | `#294437` | `#20382D` | `#335040` |
| 莓暮 / Berry | light | `#E9DEE3` | `#4C303E` | `#DFC9D3` | `#F5EDF0` | `#ECDFE6` | `#FCF6F8` |
| 莓暮 / Berry | dark | `#382631` | `#2E1C27` | `#402B39` | `#47333F` | `#3E2936` | `#543F4C` |

完整角色含text/secondary/tertiary、primary/on-primary/hover、selected、controls与独立nav文字/hover/selected/focus，见 `palettes.json`。可直接粘贴的旧token映射见 `theme-token-mapping.css`；这个CSS不含组件结构决定，唯一index writer须结合实际组件应用。

## 关键对比计算

采用WCAG sRGB相对亮度计算，不是肉眼估计。336个opaque pairs覆盖四种正文/辅助/三级/链接文字对7类内容表面（含hover/selected）、按钮两态、导航三态和控件轮廓。336项均达到声明的4.5:1或3:1。

| 主题模式 | 最低正文/链接对比 | 按钮文字 | 导航辅助最小 | 控件轮廓最小 |
| --- | ---: | ---: | ---: | ---: |
| iris-light | 4.71:1 | 7.03:1 | 4.82:1 | 3.14:1 |
| iris-dark | 4.62:1 | 8.01:1 | 5.99:1 | 3.33:1 |
| ocean-light | 4.61:1 | 6.99:1 | 4.96:1 | 3.11:1 |
| ocean-dark | 4.57:1 | 8.40:1 | 5.81:1 | 3.09:1 |
| pine-light | 4.56:1 | 6.72:1 | 5.04:1 | 3.13:1 |
| pine-dark | 4.55:1 | 7.84:1 | 5.73:1 | 3.23:1 |
| berry-light | 4.54:1 | 7.15:1 | 4.63:1 | 3.19:1 |
| berry-dark | 4.51:1 | 7.41:1 | 5.87:1 | 3.22:1 |

计算不覆盖透明叠底、混合模式、日期/项目/语义badge、禁用态、字体实际渲染和每个组件的CSS优先级，仍须真实8skin浏览器检查。尤其不要把chrome恢复为无控制的低透明度后复用上述opaque结论。

## 集成边界

- 保留localStorage `accent` 和 `iris/ocean/pine/berry` 枚举。html `data-accent` 继续承接风格；light/dark/system的外观设置独立。只换表面和偏好呈现，不重建任务DOM。
- 深导航需局部作用域：nav text、secondary、hover、selected和focus从`--nav-*`读取。不能让全局正文变白，不能让旧light primary深色字落在深导航上。saved-view小字、删除图标、页脚说明和所有focus必须同样覆盖。
- 深导航无论应用亮暗，都应使用可辨识的项目dot（如紫`#C4AFE4`、绿`#9BD6BA`、赭`#E8CB96`）；正文项目色与状态语义仍有自己的独立角色。
- 成功、警告、逾期和危险色保持语义，不被主题主色替代；它们在有色内容面上的真实对比也需核查。
- 建议chrome使用主题的实色header；需要玻璃的固定层可以保留效果，但必须用可控的不透明底面和solid回退保证小字清楚。层次主要来自色面、空间与字级，不靠把所有平面堆上重影。
- 原生radio gallery可以直接比较四种完整工作区微缩构图，当前选择使用真实checked state；旧#accentSelect只作为隐藏兼容字段。跨窗口同步原setAccentPreference时，必须同时更新radio checked，不能触发任务重建。

## 资源合同

`craft.accentLabel` 为“工作区主题”/“Workspace theme”，`craft.accentDescription` 明确侧栏/背景/面板/选中状态同时改变。现有4个accent名key不变：雾紫/海湾/松林/莓暮，对应Iris/Ocean/Pine/Berry。

新增仅5key：`craft.themeChooser` 与 `craft.themeIrisDescription` / `themeOceanDescription` / `themePineDescription` / `themeBerryDescription`。两语言现各839keys，全部834旧key保留，占位符严格相同；本子任务未bundle、未改index/CSP/版本。

## 对白与空的进一步判断

颜色能够建立大面积层次，却不能靠颜色增加不存在的信息。空间审查已确认初版列表淡中性色覆盖约95%，theme settings约96%。主任务区的过宽空面、任务元信息竖向堆叠、宽标题空带和小月历独立白卡还需同轮解决；由layout owner从真实任务与视图关系调整，不应补装饰性KPI或假内容。
