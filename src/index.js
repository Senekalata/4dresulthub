export default {
  async fetch(request, env) {

    // CORS / preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
          "cache-control": "public, max-age=300"
        }
      });
    }

    const url = new URL(request.url);


    // Home / API information
    if (
      url.pathname === "/" ||
      url.pathname === "/api"
    ) {
      return json({
        name: "4DResultHub API",
        status: "online",
        endpoints: [
          "/api/latest",
          "/api/latest.js?callback=testResults",
          "/api/history?operator=magnum",
          "/api/check?number=0650"
        ]
      });
    }


    // JSONP latest results for Blogger
    if (url.pathname === "/api/latest.js") {

      const callback =
        url.searchParams.get("callback");

      if (
        !callback ||
        !/^[A-Za-z_$][0-9A-Za-z_$]*$/.test(callback)
      ) {
        return new Response(
          "Invalid callback",
          {
            status: 400,
            headers: {
              "content-type":
                "text/plain; charset=UTF-8"
            }
          }
        );
      }


      const results =
        await getAllResults(env);

      const latest = {};


      for (const item of results) {

        if (!latest[item.operator]) {
          latest[item.operator] = item;
        }

      }


      return new Response(
        callback +
        "(" +
        JSON.stringify(latest) +
        ");",
        {
          headers: {
            "content-type":
              "application/javascript; charset=UTF-8",

            "access-control-allow-origin":
              "*",

            "cache-control":
              "public, max-age=300"
          }
        }
      );

    }


    // Latest results
    if (url.pathname === "/api/latest") {

      const results =
        await getAllResults(env);

      const latest = {};


      for (const item of results) {

        const operator =
          item.operator;

        if (!latest[operator]) {
          latest[operator] = item;
        }

      }


      return json(latest);

    }


    // Number checker
    if (url.pathname === "/api/check") {

      const number =
        url.searchParams.get("number");


      if (!/^\d{4}$/.test(number || "")) {

        return json(
          {
            error:
              "Please enter exactly 4 digits."
          },
          400
        );

      }


      const results =
        await getAllResults(env);

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


        if (
          (draw.special || [])
            .includes(number)
        ) {

          matches.push({
            operator: draw.operator,
            date: draw.date,
            draw_number: draw.draw_number,
            prize: "Special"
          });

        }


        if (
          (draw.consolation || [])
            .includes(number)
        ) {

          matches.push({
            operator: draw.operator,
            date: draw.date,
            draw_number: draw.draw_number,
            prize: "Consolation"
          });

        }

      }


      return json({
        number: number,
        total_matches: matches.length,
        matches: matches
      });

    }


    // History
    if (url.pathname === "/api/history") {

      const operator =
        url.searchParams.get("operator");

      let results =
        await getAllResults(env);


      if (operator) {

        results =
          results.filter(
            function(item) {
              return item.operator === operator;
            }
          );

      }


      return json({
        total: results.length,
        results: results
      });

    }


    // Endpoint not found
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


  for (
    const operator of operators
  ) {

    const url =
      "https://raw.githubusercontent.com/" +
      "Senekalata/4dresulthub/main/data/" +
      operator +
      ".json";


    try {

      const response =
        await fetch(url);


      if (response.ok) {

        const data =
          await response.json();


        if (Array.isArray(data)) {

          all.push(...data);

        }

      }

    } catch (error) {

      console.error(
        "Unable to load " +
        operator +
        ":",
        error
      );

    }

  }


  all.sort(
    function(a, b) {

      return String(b.date)
        .localeCompare(
          String(a.date)
        );

    }
  );


  return all;

}



function json(data, status = 200) {

  return new Response(
    JSON.stringify(
      data,
      null,
      2
    ),
    {
      status: status,

      headers: {
        "content-type":
          "application/json; charset=UTF-8",

        "access-control-allow-origin":
          "*",

        "access-control-allow-methods":
          "GET, OPTIONS",

        "access-control-allow-headers":
          "Content-Type",

        "cache-control":
          "public, max-age=300"
      }
    }
  );

}
