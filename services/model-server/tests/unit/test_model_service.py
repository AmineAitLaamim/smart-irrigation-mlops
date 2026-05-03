import asyncio
import json

from src.model_service import FallbackRegressor, ModelRegistry, grpc_handler


def test_fallback_regressor_predicts_mean():
    model = FallbackRegressor()
    assert model.predict([[1.0, 2.0, 3.0]]) == [2.0]


def test_grpc_handler_returns_json_payload():
    async def run():
        payload = json.dumps({"features": [1.0, 2.0, 3.0]}).encode("utf-8")
        result = await grpc_handler(ModelRegistry(), payload)
        decoded = json.loads(result.decode("utf-8"))
        assert "prediction" in decoded
        assert "confidence_interval" in decoded

    asyncio.run(run())
