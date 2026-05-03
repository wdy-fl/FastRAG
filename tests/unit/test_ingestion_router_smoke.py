def test_ingestion_router_importable():
    from backend.api.routers.ingestion import router
    routes = [r.path for r in router.routes]
    assert any("documents" in r for r in routes)
    assert any("ingestion-task" in r for r in routes)
