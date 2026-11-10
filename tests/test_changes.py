"""deploy/changes.py: which targets a push redeploys."""
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("changes", Path(__file__).resolve().parents[1] / "deploy" / "changes.py")
changes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(changes)
ALL = sorted(changes.realms_and_modules()[0])   # every realm that has agents


@pytest.mark.parametrize("files, web, realms, kb, bq", [
    (["README.md", "docs/architecture.md", "tests/test_catalog.py"], False, [], [], False),
    (["web/static/app.js"], True, [], [], False),
    (["agenthive/blocks.py"], True, [], [], False),
    (["agenthive/catalog/realms/smb.yaml"], True, ["smb"], [], False),
    (["agenthive/catalog/realms/enterprise__ops.yaml"], True, ["enterprise"], [], False),
    (["agenthive/tools/government.py"], True, ["government"], [], False),
    (["agenthive/tools/common.py"], True, ALL, [], False),
    (["agenthive/agents/factory.py"], True, ALL, [], False),
    (["agenthive/grounding/corpus/smb/playbook.md"], False, [], ["smb"], False),
    (["deploy/seed/bq_government.py"], False, [], [], True),
    (["deploy/deploy_engines.py"], False, ALL, [], False),
])
def test_plan(files, web, realms, kb, bq):
    got = changes.plan(files)
    assert {k: got[k] for k in ("web", "realms", "kb", "bq")} == {"web": web, "realms": realms, "kb": kb, "bq": bq}
    # every internal realm that redeploys takes the showcase segments holding its agents along
    assert bool(got["showcase"]) == bool(realms)
    assert got["engines"] == [{"edition": "internal", "realm": r} for r in realms] + \
        [{"edition": "showcase", "realm": s} for s in got["showcase"]]


def test_showcase_paths():
    seg = changes.plan(["agenthive/catalog/realms/delivery__ops.yaml"])
    assert seg["realms"] == ["delivery"] and seg["showcase"] == ["services"]
    over = changes.plan(["agenthive/catalog/editions/showcase/agents__services.yaml"])
    assert over["realms"] == [] and over["showcase"] and over["web"]
    kb = changes.plan(["agenthive/grounding/editions/showcase/corpus/services/x.md"])
    assert kb["kb"] == ["delivery"] and not kb["engines"]
    plat = changes.plan(["agenthive/grounding/corpus/platform/x.md"])
    assert plat["kb"] == ["enterprise", "platform"]


def test_explicit_targets():
    assert changes.explicit("web,smb")["realms"] == ["smb"]
    assert changes.explicit("engines")["realms"] and not changes.explicit("engines")["web"]
    assert changes.explicit("sc:services")["showcase"] == ["services"]
    assert changes.explicit("showcase")["realms"] == []
    with pytest.raises(SystemExit):
        changes.explicit("nope")
