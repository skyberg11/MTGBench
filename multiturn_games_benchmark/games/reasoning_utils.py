import re
from typing import Tuple


def extract_reasoning_and_answer(response: str) -> Tuple[str, str]:
    reasoning = ""
    answer = ""

    # Ищем ПОСЛЕДНЕЕ вхождение answer/ответ и берем все, что после него
    # Первый .* жадный, он съест весь текст до самого последнего ключевого слова
    a_match = re.search(r'.*(?:answer|ответ):\s*(.*)', response, re.DOTALL | re.IGNORECASE)
    if a_match:
        answer = a_match.group(1).strip()

    # Ищем ПЕРВОЕ вхождение reasoning/рассуждение и берем текст до последнего answer/ответ
    r_match = re.search(r'(?:reasoning|рассуждение):\s*(.*)', response, re.DOTALL | re.IGNORECASE)
    if r_match:
        reasoning_text = r_match.group(1).strip()
        # Отрезаем всё начиная с последнего вхождения answer/ответ
        cut_match = re.search(r'(.*)(?:answer|ответ):\s*', reasoning_text, re.DOTALL | re.IGNORECASE)
        if cut_match:
            reasoning = cut_match.group(1).strip()
        else:
            reasoning = reasoning_text

    # Если нашли хотя бы один из ключей
    if reasoning or answer:
        return reasoning, answer

    # Фолбек
    paragraphs = response.split('\n\n', 1)
    if len(paragraphs) == 2:
        return paragraphs[0].strip(), paragraphs[1].strip()

    return "", response.strip()


def strip_reasoning_for_context(response: str) -> str:
    _, answer = extract_reasoning_and_answer(response)
    return answer
