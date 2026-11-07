"""deploy/changes.py: which targets a push redeploys."""
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("changes", Path(__file__).resolve().parents[1] / "deploy" / "changes.py")
changes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(changes)
ALL = ["delivery", "enterprise", "government", "platform", "smb"]


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
    assert changes.plan(files) == {"web": web, "realms": realms, "kb": kb, "bq": bq}


def test_explicit_targets():
    assert changes.explicit("web,smb")["realms"] == ["smb"]
    assert changes.explicit("engines")["realms"] and not changes.explicit("engines")["web"]
    with pytest.raises(SystemExit):
        changes.explicit("nope")
