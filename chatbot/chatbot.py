import json
import os

import anyio
from dotenv import load_dotenv
from mcp import Client

from .formatters import (
    answer_ranking_followup,
    format_all_stocks,
    format_industries,
    format_ranking_result,
    format_symbols,
)
from .llm import create_llm_client


load_dotenv()



MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL"
)

LLM_MODEL = os.getenv(
    "LLM_MODEL",
    "openai/gpt-oss-120b",
)


if not MCP_SERVER_URL:

    raise RuntimeError(
        "MCP_SERVER_URL is not configured."
    )


RANKING_TOOLS = {
    "get_top_change",
    "get_bottom_change",
    "get_top_volume",
    "get_bottom_volume",
}


async def process_question(
    user_question: str,
    conversation_history: list,
):


    async with Client(
        MCP_SERVER_URL
    ) as mcp_client:


        tools_result = (
            await mcp_client.list_tools()
        )


        llm_tools = []


        for tool in tools_result.tools:

            llm_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": (
                            tool.description or ""
                        ),
                        "parameters": (
                            tool.input_schema
                        ),
                    },
                }
            )



        llm_client = create_llm_client()



        system_prompt = """
You are a factual PSX data chatbot.

Your job is to answer questions about Pakistan Stock
Exchange data using the available MCP tools.

Use an MCP tool when fresh PSX data is required.

If the user's question can be answered directly from the
previous conversation or previous chatbot response, use
that context instead of unnecessarily calling an MCP tool.

Tool selection rules:

- get_symbols:
  Use for stock symbols.

- get_industries:
  Use for available PSX industries.

- get_stocks:
  Use when the user asks for stocks belonging to a
  specific industry.

- get_top_change:
  Use for top stocks by change percentage.

- get_bottom_change:
  Use for bottom stocks by change percentage.

- get_top_volume:
  Use for top stocks by trading volume.

- get_bottom_volume:
  Use for bottom stocks by trading volume.

When an industry is mentioned, pass its exact industry
name as the industry argument.

Never invent PSX data.

Never change numbers returned by the MCP tool.

For ranking questions, the MCP result is the source
of truth.

For follow-up questions about a ranking already shown,
use the existing conversation context whenever possible.

Keep answers concise and factual.
"""



        messages = [
            {
                "role": "system",
                "content": system_prompt,
            }
        ]


        messages.extend(
            conversation_history
        )


        messages.append(
            {
                "role": "user",
                "content": user_question,
            }
        )


        try:

            response = (
                await llm_client
                .chat
                .completions
                .create(
                    model=LLM_MODEL,
                    messages=messages,
                    tools=llm_tools,
                    tool_choice="auto",
                    temperature=0,
                )
            )

        except Exception as e:

            return {
                "answer": (
                    f"LLM request failed: {str(e)}"
                ),
                "tool": None,
                "arguments": None,
            }


        assistant_message = (
            response.choices[0].message
        )



        if not assistant_message.tool_calls:

            return {
                "answer": (
                    assistant_message.content or ""
                ),
                "tool": None,
                "arguments": None,
            }



        messages.append(
            {
                "role": "assistant",
                "content": (
                    assistant_message.content or ""
                ),
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": (
                                tool_call.function.name
                            ),
                            "arguments": (
                                tool_call.function.arguments
                            ),
                        },
                    }
                    for tool_call
                    in assistant_message.tool_calls
                ],
            }
        )


        last_tool = None

        last_arguments = None


        for tool_call in (
            assistant_message.tool_calls
        ):

            tool_name = (
                tool_call.function.name
            )

            last_tool = tool_name



            try:

                arguments = json.loads(
                    tool_call.function.arguments
                )

            except json.JSONDecodeError:

                return {
                    "answer": (
                        "The chatbot received invalid "
                        "tool arguments."
                    ),
                    "tool": tool_name,
                    "arguments": None,
                }


            last_arguments = arguments



            try:

                tool_result = (
                    await mcp_client.call_tool(
                        tool_name,
                        arguments,
                    )
                )

            except Exception:

                return {
                    "answer": (
                        "I couldn't retrieve the "
                        "requested PSX data right now."
                    ),
                    "tool": tool_name,
                    "arguments": arguments,
                }


            result_text = ""


            for content in tool_result.content:

                if hasattr(
                    content,
                    "text",
                ):

                    result_text += content.text


            try:

                result_data = json.loads(
                    result_text
                )

            except json.JSONDecodeError:

                return {
                    "answer": (
                        "The PSX API returned an "
                        "invalid response."
                    ),
                    "tool": tool_name,
                    "arguments": arguments,
                }


            data = result_data.get(
                "data",
                [],
            )



            if tool_name in RANKING_TOOLS:

                followup_answer = (
                    answer_ranking_followup(
                        user_question,
                        tool_name,
                        data,
                    )
                )


                if followup_answer:

                    return {
                        "answer": followup_answer,
                        "tool": tool_name,
                        "arguments": arguments,
                    }


                answer = (
                    format_ranking_result(
                        tool_name,
                        data,
                    )
                )


                return {
                    "answer": answer,
                    "tool": tool_name,
                    "arguments": arguments,
                }


            

            if tool_name == "get_stocks":

                industry = arguments.get(
                    "industry",
                    "",
                )


                answer = format_all_stocks(
                    data,
                    industry,
                )


                return {
                    "answer": answer,
                    "tool": tool_name,
                    "arguments": arguments,
                }


            

            if tool_name == "get_symbols":

                answer = format_symbols(
                    data
                )


                return {
                    "answer": answer,
                    "tool": tool_name,
                    "arguments": arguments,
                }


            

            if tool_name == "get_industries":

                answer = format_industries(
                    data
                )


                return {
                    "answer": answer,
                    "tool": tool_name,
                    "arguments": arguments,
                }


        

        try:

            final_response = (
                await llm_client
                .chat
                .completions
                .create(
                    model=LLM_MODEL,
                    messages=messages,
                    temperature=0,
                    tool_choice="none",
                )
            )

        except Exception as e:

            return {
                "answer": (
                    f"LLM response failed: {str(e)}"
                ),
                "tool": last_tool,
                "arguments": last_arguments,
            }


        final_answer = (
            final_response
            .choices[0]
            .message
            .content
        )


        return {
            "answer": final_answer or "",
            "tool": last_tool,
            "arguments": last_arguments,
        }




def ask_chatbot(
    question: str,
    conversation_history: list,
):

    return anyio.run(
        process_question,
        question,
        conversation_history,
    )