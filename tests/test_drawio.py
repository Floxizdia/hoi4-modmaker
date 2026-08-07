import base64
import os
import tempfile
import unittest
import urllib.parse
import zlib

from app import drawio, mod_loader as ml


MODEL = """<mxGraphModel dx="1000" dy="600">
  <root>
    <mxCell id="0" />
    <mxCell id="1" parent="0" />
    <mxCell id="a" value="Reform the Army" vertex="1" parent="1">
      <mxGeometry x="200" y="40" width="120" height="60" as="geometry" />
    </mxCell>
    <mxCell id="b" value="Rebuild the Fleet" vertex="1" parent="1">
      <mxGeometry x="80" y="180" width="120" height="60" as="geometry" />
    </mxCell>
    <mxCell id="c" value="Modern &amp; Better&lt;br&gt;Doctrine" vertex="1" parent="1">
      <mxGeometry x="325" y="182" width="120" height="60" as="geometry" />
    </mxCell>
    <mxCell id="e1" edge="1" parent="1" source="a" target="b" />
    <mxCell id="e2" edge="1" parent="1" source="a" target="c" />
  </root>
</mxGraphModel>"""


def compress(model):
    """Exactly how Draw.io stores a compressed diagram body."""
    quoted = urllib.parse.quote(model, safe="~()*!.'")
    deflater = zlib.compressobj(9, zlib.DEFLATED, -15)
    packed = deflater.compress(quoted.encode()) + deflater.flush()
    return base64.b64encode(packed).decode()


class DrawioTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, content, name="tree.drawio"):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        return path

    def plain(self, model=MODEL, page="Main"):
        return self.write(f'<mxfile><diagram name="{page}">{model}</diagram></mxfile>')

    def packed(self, model=MODEL, page="Main"):
        return self.write(
            f'<mxfile><diagram name="{page}">{compress(model)}</diagram></mxfile>')


class FormatTest(DrawioTestCase):
    def test_plain_xml(self):
        focuses, pages = drawio.load(self.plain())
        self.assertEqual(pages, ["Main"])
        self.assertEqual(len(focuses), 3)

    def test_compressed(self):
        """The default .drawio save is deflated, base64'd and URL-escaped."""
        focuses, _pages = drawio.load(self.packed())
        self.assertEqual(len(focuses), 3)

    def test_both_formats_agree(self):
        self.assertEqual(drawio.load(self.plain())[0], drawio.load(self.packed())[0])

    def test_a_bare_mxgraphmodel_also_works(self):
        focuses, _pages = drawio.load(self.write(MODEL, "bare.xml"))
        self.assertEqual(len(focuses), 3)

    def test_a_file_that_is_not_xml_says_so(self):
        with self.assertRaises(drawio.DrawioError):
            drawio.load(self.write("just some notes"))

    def test_several_pages_are_listed(self):
        path = self.write(f'<mxfile><diagram name="One">{MODEL}</diagram>'
                          f'<diagram name="Two">{MODEL}</diagram></mxfile>')
        _focuses, pages = drawio.load(path)
        self.assertEqual(pages, ["One", "Two"])

    def test_a_page_with_no_boxes_is_reported(self):
        empty = "<mxGraphModel><root><mxCell id='0'/></root></mxGraphModel>"
        with self.assertRaises(drawio.DrawioError):
            drawio.load(self.plain(empty))


class LabelTest(unittest.TestCase):
    def test_html_is_stripped_from_labels(self):
        boxes, _arrows = drawio.parse_diagram(MODEL)
        labels = {b["label"] for b in boxes}
        self.assertIn("Modern & Better Doctrine", labels)

    def test_ids_are_script_safe(self):
        self.assertEqual(drawio.make_focus_id("Modern & Better Doctrine"),
                         "modern_better_doctrine")

    def test_prefix_is_applied(self):
        self.assertEqual(drawio.make_focus_id("Reform", prefix="TUR"), "TUR_reform")

    def test_duplicate_labels_get_distinct_ids(self):
        taken = set()
        first = drawio.make_focus_id("Reform", taken=taken)
        taken.add(first)
        self.assertNotEqual(drawio.make_focus_id("Reform", taken=taken), first)

    def test_an_unlabelled_box_still_gets_an_id(self):
        self.assertTrue(drawio.make_focus_id(""))


class GridTest(unittest.TestCase):
    """Draw.io coordinates are pixels at whatever spacing the author used,
    so columns come from clustering rather than from dividing by a guess."""

    def test_boxes_that_line_up_share_a_column(self):
        boxes = [{"id": "a", "label": "", "x": 100, "y": 0, "w": 120, "h": 60},
                 {"id": "b", "label": "", "x": 104, "y": 200, "w": 120, "h": 60}]
        grid = drawio.assign_grid(boxes)
        self.assertEqual(grid["a"][0], grid["b"][0])

    def test_boxes_a_box_apart_are_different_columns(self):
        boxes = [{"id": "a", "label": "", "x": 0, "y": 0, "w": 120, "h": 60},
                 {"id": "b", "label": "", "x": 200, "y": 0, "w": 120, "h": 60}]
        grid = drawio.assign_grid(boxes)
        self.assertNotEqual(grid["a"][0], grid["b"][0])

    def test_slightly_uneven_rows_still_line_up(self):
        """180 and 182 is a hand-drawn row, not two rows."""
        boxes, arrows = drawio.parse_diagram(MODEL)
        focuses = drawio.build_focuses(boxes, arrows)
        rows = {f["id"]: f["y"] for f in focuses}
        self.assertEqual(rows["rebuild_the_fleet"], rows["modern_better_doctrine"])

    def test_grid_starts_at_zero(self):
        boxes = [{"id": "a", "label": "", "x": 900, "y": 900, "w": 120, "h": 60}]
        self.assertEqual(drawio.assign_grid(boxes)["a"], (0, 0))


class ArrowTest(unittest.TestCase):
    def test_an_arrow_becomes_a_prerequisite(self):
        boxes, arrows = drawio.parse_diagram(MODEL)
        focuses = {f["id"]: f for f in drawio.build_focuses(boxes, arrows)}
        self.assertEqual(focuses["rebuild_the_fleet"]["prerequisites"], ["reform_the_army"])
        self.assertEqual(focuses["reform_the_army"]["prerequisites"], [])

    def test_flipping_reverses_the_direction(self):
        """The file cannot say which end is the prerequisite, so the user
        gets a switch."""
        boxes, arrows = drawio.parse_diagram(MODEL)
        focuses = {f["id"]: f for f in drawio.build_focuses(boxes, arrows, flip_arrows=True)}
        self.assertEqual(focuses["rebuild_the_fleet"]["prerequisites"], [])
        self.assertEqual(sorted(focuses["reform_the_army"]["prerequisites"]),
                         ["modern_better_doctrine", "rebuild_the_fleet"])

    def test_an_arrow_to_nothing_is_ignored(self):
        model = MODEL.replace('source="a" target="c"', 'source="a" target="ghost"')
        boxes, arrows = drawio.parse_diagram(model)
        focuses = drawio.build_focuses(boxes, arrows)   # must not raise
        self.assertEqual(len(focuses), 3)


class OutputTest(DrawioTestCase):
    def build(self):
        boxes, arrows = drawio.parse_diagram(MODEL)
        return drawio.build_focuses(boxes, arrows, prefix="TUR")

    def test_the_tree_parses_with_the_apps_own_parser(self):
        focuses = self.build()
        folder = os.path.join(self.tmp.name, "common", "national_focus")
        os.makedirs(folder)
        path = os.path.join(folder, "t.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(drawio.format_tree("tur_imported", "TUR", focuses))

        tree = ml.parse_focus_trees(path)[0]
        self.assertEqual(tree["id"], "tur_imported")
        self.assertEqual(tree["country_tags"], ["TUR"])
        self.assertEqual(len(tree["focuses"]), 3)

    def test_prerequisites_survive_as_separate_and_blocks(self):
        """Two arrows into one box means it needs both, so they have to be
        separate prerequisite blocks - one block would mean 'either'."""
        focuses = [{"id": "c", "label": "C", "x": 0, "y": 1, "prerequisites": ["a", "b"]}]
        text = drawio.format_tree("t", "TUR", focuses)
        folder = os.path.join(self.tmp.name, "common", "national_focus")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "u.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        focus = ml.parse_focus_trees(path)[0]["focuses"][0]
        self.assertEqual(focus["prerequisite_groups"], [["a"], ["b"]])

    def test_braces_balance(self):
        text = drawio.format_tree("tur_imported", "TUR", self.build())
        self.assertEqual(text.count("{"), text.count("}"))

    def test_localisation_covers_every_focus(self):
        focuses = self.build()
        loc = drawio.format_localisation(focuses)
        for focus in focuses:
            self.assertIn(f' {focus["id"]}:0 ', loc)
            self.assertIn(f' {focus["id"]}_desc:0 ', loc)

    def test_quotes_in_a_drawn_name_are_escaped(self):
        loc = drawio.format_localisation(
            [{"id": "a", "label": 'The "Big" Push', "x": 0, "y": 0, "prerequisites": []}])
        self.assertIn('\\"Big\\"', loc)


if __name__ == "__main__":
    unittest.main()
