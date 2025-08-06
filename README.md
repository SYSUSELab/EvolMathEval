# EvolMathEval

Please refer to main.py for the specific execution flow.

## Seed Problem Initialization:
formula_generation.py",

## Approximate Replacement:
Approximate_substitution.py

## Useless Mathematical Condition:
trusted_gpt.py --step UselessCondition

## Misleading Mathematical Condition:
trusted_gpt.py --step ConfusedCondition

questionGeneration.py

## Problem Polishing:
trusted_gpt.py --step FormulaClarifier

## Misleading Textual Condition:
trusted_gpt.py --step MisleadingCondition

## Background Information Generation:
trusted_gpt.py --step ContextGen

## Irrelevant Topic Condition:
trusted_gpt.py --step AddCondition

## Crossover Operator:
cross.py

## Fitness Function:
Evolutionary_scoring.py
fitness.py

## Secondary evaluation:
extract_low_difficulty.py  
trusted_gpt.py --step MisleadingCondition
trusted_gpt.py --step ContextGen
trusted_gpt.py --step AddCondition
cross.py  
combine_datasets.py  
