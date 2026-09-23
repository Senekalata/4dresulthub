export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Home / API information
    if (url.pathname === "/" || url.pathname === "/api") {
      return json({
        name: "4DResultHub API",
        status: "online",
        endpoints: [
          "/api/latest",
          "/api/history?operator=magnum",
          "/api/check?number=0650"
        ]
      });
    }

    // Latest results
    if (url.pathname === "/api/latest") {
      const results = await getAllResults(env);

      const latest = {};

      for (const item of results) {
        const operator = item.operator;

        if (!latest[operator]) {
          latest[operator] = item;
        }
      }

      return json(latest);
    }

    // Number checker
    if (url.pathname === "/api/check") {
      const number = url.searchParams.get("number");

      if (!/^\d{4}$/.test(number || "")) {
        return json(
          {
            error: "Please enter exactly 4 digits."
          },
          400
        );
      }

      const results = await getAllResults(env);
      const matches = [];

      for (const draw of results) {
        if (draw.first === number) {
          matches.push({
            operator: draw.operator,
            date: draw.date,
            draw_number: draw.draw_number,
            prize: "1st Prize"
          });
        }

        if (draw.second === number) {
          matches.push({
            operator: draw.operator,
            date: draw.date,
            draw_number: draw.draw_number,
            prize: "2nd Prize"
          });
        }

        if (draw.third === number) {
          matches.push({
            operator: draw.operator,
            date: draw.date,
            draw_number: draw.draw_number,
            prize: "3rd Prize"
          });
        }

        if ((draw.special || []).includes(number)) {
          matches.push({
            operator: draw.operator,
            date: draw.date,
            draw_number: draw.draw_number,
            prize: "Special"
          });
        }

        if ((draw.consolation || []).includes(number)) {
          matches.push({
            operator: draw.operator,
            date: draw.date,
            draw_number: draw.draw_number,
            prize: "Consolation"
          });
        }
      }

      return json({
        number,
        total_matches: matches.length,
        matches
      });
    }

    // History
    if (url.pathname === "/api/history") {
      const operator = url.searchParams.get("operator");

      let results = await getAllResults(env);

      if (operator) {
        results = results.filter(
          item => item.operator === operator
        );
      }

      return json({
        total: results.length,
        results
      });
    }

    return json(
      {
        error: "Endpoint not found"
      },
      404
    );
  }
};


async function getAllResults(env) {
  const operators = [
    "magnum",
    "damacai",
    "toto",
    "singapore"
  ];

  const all = [];

  for (const operator of operators) {
    const url =
      `https://raw.githubusercontent.com/Senekalata/4dresulthub/main/data/${operator}.json`;

    try {
      const response = await fetch(url);

      if (response.ok) {
        const data = await response.json();

        if (Array.isArray(data)) {
          all.push(...data);
        }
      }
    } catch (error) {
      console.error(
        `Unable to load ${operator}:`,
        error
      );
    }
  }

  all.sort((a, b) =>
    String(b.date).localeCompare(String(a.date))
  );

  return all;
}


function json(data, status = 200) {
  return new Response(
    JSON.stringify(data, null, 2),
    {
      status,
      headers: {
        "content-type": "application/json; charset=UTF-8",
        "access-control-allow-origin": "*",
        "cache-control": "public, max-age=300"
      }
    }
  );
}
