"""Lilly P2/P3/P4 names are exported from moira and moira.facade with module identity."""
import moira
import moira.facade as facade
import moira.horary_considerations as considerations
import moira.horary_moon as moon
import moira.horary_perfection_routes as routes
import moira.horary_reception as reception


def test_lilly_layers_share_object_identity_through_root_and_facade():
    for module in (reception, moon, considerations):
        for name in module.__all__:
            assert name in moira.__all__ and name in facade.__all__, name
            assert getattr(moira, name) is getattr(module, name) is getattr(facade, name), name
    for name in ("lilly_perfection_routes_at", "LillyPerfectionReadings", "LillyRouteConditions",
                 "LILLY_BOOK_II_PRACTICE", "LillyRefranationReading", "LillyFrustrationReading",
                 "LillyCollectionReading", "LillyDwellingReading"):
        assert getattr(moira, name) is getattr(routes, name) is getattr(facade, name)


def test_facade_methods_exist():
    for method in ("lilly_reception_at", "lilly_moon_trace_at", "lilly_void_of_course_at",
                   "lilly_perfection_routes_at"):
        assert callable(getattr(moira.Moira, method))
