"""解析体检探针集合。

新增一项检查只需在此注册，check.py 不需要改动。
"""

from probes.base import DocSnapshot, Finding, Level, PageSnapshot, Probe, Span, worst
from probes.bbox import BBoxProbe
from probes.encoding import EncodingProbe
from probes.header_footer import HeaderFooterProbe
from probes.heading import HeadingProbe
from probes.table import TableProbe
from probes.text_layer import TextLayerProbe


def default_probes(with_tables: bool = True) -> list[Probe]:
    probes: list[Probe] = [
        TextLayerProbe(),
        EncodingProbe(),
        BBoxProbe(),
        HeadingProbe(),
        HeaderFooterProbe(),
    ]
    if with_tables:
        probes.append(TableProbe())
    return probes


__all__ = [
    "BBoxProbe",
    "DocSnapshot",
    "EncodingProbe",
    "Finding",
    "HeaderFooterProbe",
    "HeadingProbe",
    "Level",
    "PageSnapshot",
    "Probe",
    "Span",
    "TableProbe",
    "TextLayerProbe",
    "default_probes",
    "worst",
]
