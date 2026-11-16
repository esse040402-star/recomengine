import unittest
from normalization import normalize, resolve, REGISTRY, GROUPS, parent_codes
from sync_taxonomy import sync_igdb
import tempfile
from pathlib import Path

class VocabularyTests(unittest.TestCase):
    def test_all_aliases(self):
        for code,names in GROUPS.items():
            for n in names:
                self.assertEqual(resolve("steam.store_tags", n)["code"], code)
    def test_separate_concepts(self):
        for a,b in [("Building","City Builder"),("Turn-Based","Turn-Based Strategy"),
                    ("Top-Down","Isometric"),("Roguelike","Roguelite"),("Farming","Farming Sim")]:
            self.assertNotEqual(resolve("steam.store_tags",a)["code"],resolve("steam.store_tags",b)["code"])
    def test_synonyms(self):
        for a,b in [("RPG","Role-playing (RPG)"),("Simulator","Simulation"),
                    ("Singleplayer","Single player"),("Sci-fi","Science fiction"),("Idler","Idle")]:
            self.assertEqual(resolve("steam.store_tags",a)["code"],resolve("igdb.keywords",b)["code"])
    def test_unknown_and_duplicates(self):
        p={"steam":{"type":"game","platforms":{"windows":True},"genres":[{"id":1,"description":"액션"}]},
           "steam_tags":{"values":["Action","Unknown future tag"]},
           "igdb":{"status":"ok","game":{"themes":[{"id":1,"name":"Action"}],"keywords":[{"id":999999}]}}}
        n=normalize(p)
        self.assertEqual(n["codes"].count("genre:action"),1)
        self.assertEqual(len(n["evidence"]["genre:action"]),3)
        self.assertEqual(len(n["unmapped"]),2)
        self.assertTrue(n["recommendable"])
    def test_numeric_unknowns_and_platforms(self):
        p={"steam":{"type":"game"},"igdb":{"status":"ok","game":{"platforms":[{"name":"Android"}]},
             "time_to_beat_seconds":[{"normally":7200,"hastily":0,"count":10}]}}
        n=normalize(p)
        self.assertFalse(n["recommendable"])
        self.assertEqual(n["completion_hours"][0]["normally"],2)
        self.assertIsNone(n["completion_hours"][0]["hastily"])
        self.assertIsNone(n["price"]["amount"])
        self.assertIsNone(n["ratings"]["steam_positive_ratio"])
        p["steam"]["platforms"]={"windows":True}
        self.assertTrue(normalize(p)["recommendable"])
    def test_counts_not_overwriting(self):
        def fetch(endpoint,query):
            if endpoint.endswith("/count"):return {"count":1}
            return [] if "id > 1;" in query else [{"id":1,"name":"Action"}]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"catalog.json"
            r=sync_igdb(fetch,p)
            self.assertTrue(r["complete"])
            with self.assertRaises(FileExistsError):sync_igdb(fetch,p)
    def test_parent_separation(self):
        self.assertIn("tag:building",parent_codes(["tag:city_builder"]))
        n=normalize({"steam_tags":{"values":["City Builder"]}})
        self.assertNotIn("tag:building",n["codes"])
        self.assertIn("tag:building",n["parent_codes"])

if __name__ == "__main__":
    unittest.main()
