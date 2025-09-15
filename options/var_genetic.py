import re
import random
import warnings
from sys import argv
from tqdm import trange, tqdm
from functools import lru_cache
from compression import get_compressed

# --- CACHING FOR PERFORMANCE ---
@lru_cache(maxsize=None)
def evaluate_fitness(code, original_vars, chromosome_tuple):
    chromosome = list(chromosome_tuple)
    mapping = dict(zip(original_vars, chromosome))

    def update(m: re.Match[str]):
        return mapping.get(m[0], m[0])

    bruted_code = re.sub(VAR_PAT, update, code)
    
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=SyntaxWarning)
        compressed_code = get_compressed(bruted_code, max_brute=1_000, use_tqdm=False, check_syntax=False)

    fitness = -len(compressed_code)
    return fitness, bruted_code, compressed_code

# --- GENETIC ALGORITHM OPERATORS ---

def create_individual(n_vars):
    """
    Creates a random chromosome by sampling `n_vars` from the entire alphabet.
    """
    return random.sample(VARNAMES, n_vars)

def tournament_selection(population, fitnesses):
    tournament = random.sample(list(zip(population, fitnesses)), TOURNAMENT_SIZE)
    return max(tournament, key=lambda item: item[1])[0]

def ordered_crossover(parent1, parent2):
    size = len(parent1)
    child = [None] * size
    start, end = sorted(random.sample(range(size), 2))
    child[start:end] = parent1[start:end]
    p2_idx = 0
    for i in range(size):
        if child[i] is None:
            while parent2[p2_idx] in child:
                p2_idx += 1
            child[i] = parent2[p2_idx]
    return child

def mutate(individual):
    """Applies two types of mutation to an individual."""
    # 1. Swap Mutation (reorders existing letters)
    if random.random() < SWAP_MUTATION_RATE:
        idx1, idx2 = random.sample(range(len(individual)), 2)
        individual[idx1], individual[idx2] = individual[idx2], individual[idx1]

    # 2. Replace Mutation (introduces new letters)
    if random.random() < REPLACE_MUTATION_RATE:
        unused_vars = list(set(VARNAMES) - set(individual))
        if unused_vars:
            idx_to_replace = random.randrange(len(individual))
            new_var = random.choice(unused_vars)
            individual[idx_to_replace] = new_var
            
    return individual


# --- MAIN GENETIC ALGORITHM FUNCTION ---

def do_genetic_optimization(code: str, use_tqdm=True, log_best=True):
    code = code.strip()
    original_vars = sorted(list(set(re.findall(VAR_PAT, code))))
    n_vars = len(original_vars)
    
    if n_vars == 0:
        print("No variables found to optimize.")
        return code, get_compressed(code)

    print(f"Optimizing {n_vars} variable names: {', '.join(original_vars)}")

    # 1. INITIALIZATION
    population = [create_individual(n_vars) for _ in range(POPULATION_SIZE)]
    
    best_overall_fitness = -float('inf')
    best_bruted_code = None
    best_compressed_code = None

    # --- EVOLUTION LOOP ---
    iterator = trange(GENERATIONS) if use_tqdm else range(GENERATIONS)
    for gen in iterator:
        # 2. FITNESS EVALUATION
        fitnesses = [evaluate_fitness(code, tuple(original_vars), tuple(ind))[0] for ind in population]
        
        current_best_fitness = max(fitnesses)
        if current_best_fitness > best_overall_fitness:
            best_overall_fitness = current_best_fitness
            best_idx = fitnesses.index(best_overall_fitness)
            best_individual = population[best_idx]
            
            _, bruted, compressed = evaluate_fitness(code, tuple(original_vars), tuple(best_individual))
            best_bruted_code = bruted
            best_compressed_code = compressed
            
            # <-- CHANGE: Updated the logging block to match your request
            if log_best:
                print(f"\nNew best {len(code)}b => {len(best_compressed_code)}b! (Gen: {gen})")
                print(best_bruted_code)
                print()
                print(best_compressed_code.hex())
                print('=' * 50)


        if use_tqdm:
            # Check if best_compressed_code is not None before accessing its length
            best_len = len(best_compressed_code) if best_compressed_code else 'inf'
            iterator.set_description(f"Gen {gen} | Best: {best_len}b")
            
        # 3. SELECTION & REPRODUCTION
        sorted_population = [x for _, x in sorted(zip(fitnesses, population), key=lambda pair: pair[0], reverse=True)]
        
        next_generation = []
        next_generation.extend(sorted_population[:ELITE_SIZE])
        
        while len(next_generation) < POPULATION_SIZE:
            parent1 = tournament_selection(population, fitnesses)
            parent2 = tournament_selection(population, fitnesses)
            
            child = ordered_crossover(parent1, parent2)
            child = mutate(child)
            
            next_generation.append(child)
            
        population = next_generation

    return best_bruted_code, best_compressed_code


# --- GENETIC ALGORITHM PARAMETERS ---
POPULATION_SIZE = 1000
GENERATIONS = 10000 # usually like 100 is enough but sometimes you want more.
ELITE_SIZE = 30
TOURNAMENT_SIZE = 10
SWAP_MUTATION_RATE = 0.05     # Probability of swapping order
REPLACE_MUTATION_RATE = 0.05  # Probability of swapping a letter for a new one

# --- ORIGINAL CODE SETUP ---
VARNAMES = list("abcdefghijklmnopqrstuvwxyz")
VAR_PAT = re.compile(r"\b(?!p\(|p=lambda)(?<!\"|'|%)(?<!b'%)(?<!.%)[a-zA-Z_](?!\"|')\b(?<!def p)")

# (?<!key=)

if __name__ == "__main__":
    code = r"""
import re
def p(n):t=f'{n+[*zip(*n)]}';g=re.sub("[, ]","",t+t[::-1]);r={s+max(g,key=t.count)*len(e)+s if e else i*3for a,s,i,e in re.findall(r"(?=((([^%s])\3+)((?:(?!\3|]|\)).)*)\3))"%max(g,key=t.count),g)};r=([g for g in{*t}if t.count(g)<3]or[max(g,key=t.count)])+[g*3for g in{*t}if t.count(g)==6]+sorted({g for g in r if str(r).count(g)<2},key=len);return[[int(r[~min(e,len(r)*2-1+~e,l,len(r)*2-1+~l)][min(abs(e-l),abs(len(r)*2-1+~e-l))])for l in range(len(r)*2-1)]for e in range(len(r)*2-1)]
"""
    if len(argv) > 1:
        code = bytes.fromhex(argv[1]).decode('l1')

    bruted, compressed = do_genetic_optimization(code)

    print("=" * 50)
    print(f"Best code found | {len(bruted)}b => {len(compressed)}b\n{bruted}\n\n{compressed.hex()}")
    print("=" * 50)
