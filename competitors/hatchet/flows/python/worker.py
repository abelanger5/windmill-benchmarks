from functools import cache
from pydantic import BaseModel
from hatchet_sdk import Context, Hatchet

hatchet = Hatchet(debug=True)

class FibonacciInput(BaseModel):
    n: int

class FibonacciTriggerInput(BaseModel):
    n: int
    iterations: int
    parallel: bool

class FibonacciOutput(BaseModel):
    result: int

class FibonacciTriggerOutput(BaseModel):
    results: list[FibonacciOutput]

@cache
def fibo(n: int) -> int:
    if n <= 1:
        return n

    return fibo(n - 1) + fibo(n - 2)

@hatchet.task(input_validator=FibonacciInput)
def compute_fibonacci(input: FibonacciInput, _: Context) -> FibonacciOutput:
    return FibonacciOutput(result=fibo(input.n))

@hatchet.task(input_validator=FibonacciTriggerInput)
async def fibonacci_parent(
    input: FibonacciTriggerInput, _: Context
) -> FibonacciTriggerOutput:
    if input.parallel:
        return FibonacciTriggerOutput(
            results=await compute_fibonacci.aio_run_many(
                [
                    compute_fibonacci.create_bulk_run_item(FibonacciInput(n=input.n))
                    for _ in range(input.iterations)
                ]
            )
        )

    return FibonacciTriggerOutput(
        results=[
            await compute_fibonacci.aio_run(FibonacciInput(n=input.n))
            for _ in range(input.iterations)
        ]
    )

def main() -> None:
    worker = hatchet.worker(
        slots=100, name="fibo-worker", workflows=[fibonacci_parent, compute_fibonacci]
    )
    worker.start()

if __name__ == "__main__":
    main()